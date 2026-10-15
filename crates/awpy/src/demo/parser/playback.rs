use pbdems2::{DemoParser, PreparedPlayback, PropertyFilter};

use crate::entity::{ClassInfo, SerializerContainer};
use crate::error::{Error, Result};

use super::super::adapter::MetadataUpdate;
use super::{Context, Cs2Adapter, DEFAULT_TICK_INTERVAL, GameEvent, HEADER_SIZE, Parser};
use crate::datasets::EventDatasetSelection;

/// Compact state needed before a cold keyframe: no entity snapshots are cached.
pub(crate) struct CombatBootstrap {
    updates: Vec<MetadataUpdate>,
    events: Vec<GameEvent>,
    pub(crate) class_schema_changed: bool,
}

impl Parser {
    fn demo_parser(&self) -> Result<DemoParser<'_>> {
        DemoParser::new(self.data()).map_err(Error::from)
    }

    fn prepared(&self) -> Result<&PreparedPlayback<Cs2Adapter>> {
        if let Some(prepared) = self.prepared_cache.get() {
            return Ok(prepared);
        }

        let _guard = self.prepared_lock.lock().map_err(|_| Error::Parse {
            context: "prepared-playback cache lock poisoned".into(),
        })?;
        if self.prepared_cache.get().is_none() {
            let prepared = self
                .demo_parser()?
                .prepare(Cs2Adapter::default(), DEFAULT_TICK_INTERVAL)?;
            self.prepared_cache.set(prepared).unwrap_or_else(|_| {
                unreachable!("prepared-playback cache initialized while locked")
            });
        }
        Ok(self
            .prepared_cache
            .get()
            .expect("prepared-playback cache populated"))
    }

    /// Parse send tables from the signon stream.
    pub fn parse_send_tables(&self) -> Result<SerializerContainer> {
        Ok(self.prepared()?.initial_state().serializers().clone())
    }

    /// Parse network class information from the signon stream.
    pub fn parse_class_info(&self) -> Result<ClassInfo> {
        Ok(self.prepared()?.initial_state().class_info().clone())
    }

    /// Parse all initialization data through `DEM_SyncTick`.
    pub fn parse_init(&self) -> Result<Context> {
        Ok(self.prepared()?.initial_state().clone())
    }

    /// Parse the demo to a specific tick, restoring the nearest full packet.
    pub fn parse_to_tick(&self, target_tick: i32) -> Result<Context> {
        let parser = self.demo_parser()?;
        self.prepared()?.session(parser)?.parse_to_tick(target_tick)
    }

    /// Parse the entire demo, calling a callback once per completed tick.
    pub fn run_to_end<F>(&self, on_tick: F) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let parser = self.demo_parser()?;
        self.prepared()?.session(parser)?.run_to_end(on_tick)?;
        Ok(())
    }

    /// Parse the entire demo while materializing only selected entity classes.
    pub fn run_to_end_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let parser = self.demo_parser()?;
        self.prepared()?
            .session(parser)?
            .run_to_end_filtered(class_filter, on_tick)?;
        Ok(())
    }

    /// Parse entities and game events in one filtered pass.
    pub fn run_to_end_with_events_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        let parser = self.demo_parser()?;
        let mut session = self.prepared()?.session(parser)?;
        session.adapter_mut().enable_events();
        session.run_to_end_filtered_with_adapter(class_filter, |state, adapter| {
            on_tick(state, adapter.tick_events());
            adapter.clear_tick_events();
        })?;
        Ok(())
    }

    /// Parse entities and only selected legacy events in one filtered pass.
    ///
    /// Raw event payloads are omitted: callers of this path consume the decoded
    /// legacy key/value pairs and avoid allocating protobuf bytes they will not
    /// use.
    pub(crate) fn run_to_end_with_legacy_events_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        event_names: &std::collections::HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        self.run_legacy_event_segment(class_filter, event_names, None, None, &mut on_tick)
    }

    /// Resolve a fixed property plan, retaining full decoding for schema changes.
    pub(crate) fn property_filter(
        &self,
        classes: Vec<(&str, Vec<String>)>,
    ) -> Result<Option<PropertyFilter>> {
        let prepared = self.prepared()?;
        Ok((!prepared.index().has_schema_changes())
            .then(|| PropertyFilter::new(prepared.initial_state().serializers(), classes)))
    }

    /// Record metadata and combat events in source order while skipping entity payloads.
    pub(crate) fn combat_bootstrap(&self) -> Result<&CombatBootstrap> {
        if let Some(bootstrap) = self.combat_bootstrap.get() {
            return Ok(bootstrap);
        }
        let _guard = self
            .combat_bootstrap_lock
            .lock()
            .map_err(|_| Error::Parse {
                context: "combat metadata cache lock poisoned".into(),
            })?;
        if self.combat_bootstrap.get().is_none() {
            let parser = self.demo_parser()?;
            let mut session = self.prepared()?.session(parser)?;
            session.adapter_mut().metadata_only = true;
            session
                .adapter_mut()
                .enable_legacy_events(EventDatasetSelection::ALL.legacy_event_names(), false);
            let mut bootstrap = CombatBootstrap {
                updates: Vec::new(),
                events: Vec::new(),
                class_schema_changed: false,
            };
            session.run_to_end_filtered_with_adapter(
                &std::collections::HashSet::new(),
                |_, adapter| {
                    bootstrap.updates.append(&mut adapter.metadata_updates);
                    bootstrap.events.append(&mut adapter.tick_events);
                    bootstrap.class_schema_changed |= adapter.class_schema_changed;
                },
            )?;
            self.combat_bootstrap
                .set(bootstrap)
                .unwrap_or_else(|_| unreachable!("combat metadata initialized while locked"));
        }
        Ok(self
            .combat_bootstrap
            .get()
            .expect("combat metadata populated"))
    }

    /// Decode entities in a segment and join authoritative events by completed tick.
    /// Events before the full-packet command on its tick still belong to this segment.
    pub(crate) fn run_legacy_event_segment<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        event_names: &std::collections::HashSet<&str>,
        properties: Option<&PropertyFilter>,
        segment: Option<(Option<usize>, i32)>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        let parser = self.demo_parser()?;
        let prepared = self.prepared()?;
        let mut session = match properties {
            Some(properties) => prepared.session_with_properties(parser, properties.clone())?,
            None => prepared.session(parser)?,
        };
        if let Some((start, end_tick)) = segment {
            let bootstrap = self.combat_bootstrap()?;
            if let Some(start) = start {
                let end = bootstrap
                    .updates
                    .partition_point(|update| update.offset < start + HEADER_SIZE);
                session
                    .adapter_mut()
                    .seed_metadata(&bootstrap.updates[..end]);
            }
            let mut cursor = None;
            session.decode_segment(
                start.map(|offset| offset + HEADER_SIZE),
                end_tick,
                class_filter,
                |state| {
                    let begin = *cursor.get_or_insert_with(|| {
                        bootstrap
                            .events
                            .partition_point(|event| event.tick < state.tick())
                    });
                    let end = begin
                        + bootstrap.events[begin..]
                            .partition_point(|event| event.tick == state.tick());
                    on_tick(state, &bootstrap.events[begin..end]);
                    cursor = Some(end);
                },
            )?;
        } else {
            session
                .adapter_mut()
                .enable_legacy_events(event_names.iter().copied(), false);
            session.run_to_end_filtered_with_adapter(class_filter, |state, adapter| {
                on_tick(state, adapter.tick_events());
                adapter.clear_tick_events();
            })?;
        }
        Ok(())
    }

    /// Byte offsets relative to the post-header stream and ticks of full packets.
    pub fn full_packet_offsets(&self) -> Result<Vec<(usize, i32)>> {
        Ok(self
            .prepared()?
            .index()
            .full_packets()
            .iter()
            .map(|position| (position.offset() - HEADER_SIZE, position.tick()))
            .collect())
    }

    /// Every distinct post-signon tick in ascending stream order.
    pub fn distinct_ticks(&self) -> Result<Vec<i32>> {
        Ok(self.prepared()?.index().distinct_ticks().to_vec())
    }

    /// Decode one full-packet-bounded segment for parallel consumers.
    pub fn decode_segment<F>(
        &self,
        start: Option<usize>,
        end_tick: i32,
        class_filter: &std::collections::HashSet<&str>,
        on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let parser = self.demo_parser()?;
        self.prepared()?.session(parser)?.decode_segment(
            start.map(|offset| offset + HEADER_SIZE),
            end_tick,
            class_filter,
            on_tick,
        )?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::demo::command::{dem, ge, svc};
    use awpy_proto::proto::CsvcMsgUpdateStringTable;
    use awpy_proto::proto::{
        CDemoClassInfo, CDemoFullPacket, CDemoPacket, CDemoSendTables, CMsgSource1LegacyGameEvent,
        CMsgSource1LegacyGameEventList, CsvcMsgCreateStringTable, EDemoCommands,
        c_msg_source1_legacy_game_event::KeyT,
        c_msg_source1_legacy_game_event_list::{DescriptorT, KeyT as DescriptorKey},
    };
    use prost::Message;

    fn varint(mut value: u64, bytes: &mut Vec<u8>) {
        while value >= 128 {
            bytes.push(value as u8 | 128);
            value >>= 7;
        }
        bytes.push(value as u8);
    }

    fn command(bytes: &mut Vec<u8>, kind: i32, tick: i32, body: &[u8]) {
        for value in [kind as u32 as u64, tick as u32 as u64, body.len() as u64] {
            varint(value, bytes);
        }
        bytes.extend_from_slice(body);
    }

    fn packet(kind: u32, body: &[u8]) -> Vec<u8> {
        let mut bits = Vec::new();
        let mut write = |value: u64, count: usize| {
            bits.extend((0..count).map(|i| (value >> i) & 1 != 0));
        };
        let extra = if kind < 16 {
            0
        } else if kind < 256 {
            4
        } else if kind < 4096 {
            8
        } else {
            28
        };
        let tag = match extra {
            0 => 0,
            4 => 16,
            8 => 32,
            _ => 48,
        };
        write(u64::from((kind & 15) | tag), 6);
        write(u64::from(kind >> 4), extra);
        let mut length = Vec::new();
        varint(body.len() as u64, &mut length);
        for byte in length.iter().chain(body) {
            write(u64::from(*byte), 8);
        }
        let mut bytes = vec![0; bits.len().div_ceil(8)];
        for (i, bit) in bits.into_iter().enumerate() {
            bytes[i / 8] |= u8::from(bit) << (i % 8);
        }
        CDemoPacket { data: Some(bytes) }.encode_to_vec()
    }

    fn event(label: &str) -> Vec<u8> {
        packet(
            ge::SOURCE1_LEGACY_GAME_EVENT,
            &CMsgSource1LegacyGameEvent {
                eventid: Some(7),
                keys: vec![KeyT {
                    r#type: Some(1),
                    val_string: Some(label.into()),
                    ..Default::default()
                }],
                ..Default::default()
            }
            .encode_to_vec(),
        )
    }

    fn fixture(malformed_entities: bool) -> Parser {
        let mut bytes = b"PBDEMS2\0".to_vec();
        bytes.resize(16, 0);
        command(
            &mut bytes,
            EDemoCommands::DemSendTables as i32,
            -1,
            &CDemoSendTables {
                data: Some(vec![0]),
            }
            .encode_to_vec(),
        );
        command(
            &mut bytes,
            EDemoCommands::DemClassInfo as i32,
            -1,
            &CDemoClassInfo::default().encode_to_vec(),
        );
        let descriptors = CMsgSource1LegacyGameEventList {
            descriptors: vec![DescriptorT {
                eventid: Some(7),
                name: Some("weapon_fire".into()),
                keys: vec![DescriptorKey {
                    r#type: Some(1),
                    name: Some("weapon".into()),
                }],
            }],
        };
        command(
            &mut bytes,
            dem::SIGNON_PACKET,
            -1,
            &packet(
                ge::SOURCE1_LEGACY_GAME_EVENT_LIST,
                &descriptors.encode_to_vec(),
            ),
        );
        command(&mut bytes, EDemoCommands::DemSyncTick as i32, 0, &[]);
        let table = CsvcMsgCreateStringTable {
            name: Some("instancebaseline".into()),
            num_entries: Some(0),
            user_data_fixed_size: Some(true),
            user_data_size: Some(1),
            user_data_size_bits: Some(8),
            ..Default::default()
        };
        command(
            &mut bytes,
            dem::PACKET,
            5,
            &packet(svc::CREATE_STRING_TABLE, &table.encode_to_vec()),
        );
        let mut bits = vec![true, true, false]; // next index, name, no history
        for byte in b"12\0" {
            bits.extend((0..8).map(|i| (byte >> i) & 1 != 0));
        }
        bits.push(true); // user data
        bits.extend((0..8).map(|i| (171 >> i) & 1 != 0));
        let mut data = vec![0; bits.len().div_ceil(8)];
        for (i, bit) in bits.into_iter().enumerate() {
            data[i / 8] |= u8::from(bit) << (i % 8);
        }
        let update = CsvcMsgUpdateStringTable {
            table_id: Some(0),
            num_changed_entries: Some(1),
            string_data: Some(data),
        };
        command(
            &mut bytes,
            dem::PACKET,
            7,
            &packet(svc::UPDATE_STRING_TABLE, &update.encode_to_vec()),
        );
        if malformed_entities {
            command(
                &mut bytes,
                dem::PACKET,
                8,
                &packet(svc::PACKET_ENTITIES, &[128]),
            );
        }
        let full = CDemoFullPacket {
            packet: Some(CDemoPacket {
                data: Some(Vec::new()),
            }),
            ..Default::default()
        }
        .encode_to_vec();
        command(&mut bytes, dem::FULL_PACKET, 10, &full);
        command(&mut bytes, dem::PACKET, 20, &event("before"));
        command(&mut bytes, dem::FULL_PACKET, 20, &full);
        command(&mut bytes, dem::PACKET, 20, &event("after"));
        command(&mut bytes, dem::FULL_PACKET, 30, &full);
        command(&mut bytes, dem::PACKET, 31, &event("last"));
        command(&mut bytes, dem::STOP, 32, &[]);
        Parser::from_bytes(bytes)
    }

    #[test]
    fn metadata_preparation_skips_entity_payloads() {
        assert!(fixture(true).combat_bootstrap().is_ok());
    }

    #[test]
    fn parallel_segments_restore_string_tables_created_after_signon() {
        let parser = fixture(false);
        let start = parser.full_packet_offsets().unwrap()[1].0;
        let names = EventDatasetSelection::ALL.legacy_event_names();
        let mut restored = false;
        parser
            .run_legacy_event_segment(
                &Default::default(),
                &names,
                None,
                Some((Some(start), i32::MAX)),
                |ctx, _| {
                    restored = ctx.string_tables().find_table("instancebaseline").is_some();
                },
            )
            .unwrap();
        assert!(restored);
    }

    #[test]
    fn parallel_segments_restore_late_class_baselines() {
        let parser = fixture(false);
        let start = parser.full_packet_offsets().unwrap()[1].0;
        let names = EventDatasetSelection::ALL.legacy_event_names();
        let mut baseline = None;
        parser
            .run_legacy_event_segment(
                &Default::default(),
                &names,
                None,
                Some((Some(start), i32::MAX)),
                |ctx, _| {
                    baseline = ctx
                        .string_tables()
                        .instance_baseline(12)
                        .map(<[u8]>::to_vec);
                },
            )
            .unwrap();
        assert_eq!(baseline, Some(vec![171]));
    }

    #[test]
    fn events_before_a_keyframe_on_its_tick_keep_source_order() {
        let parser = fixture(false);
        let start = parser.full_packet_offsets().unwrap()[1].0;
        let names = EventDatasetSelection::ALL.legacy_event_names();
        let mut labels = Vec::new();
        parser
            .run_legacy_event_segment(
                &Default::default(),
                &names,
                None,
                Some((Some(start), i32::MAX)),
                |_, events| {
                    labels.extend(events.iter().map(|event| event.keys[0].1.clone()));
                },
            )
            .unwrap();
        assert_eq!(labels, ["before", "after", "last"]);
    }

    #[test]
    fn later_schema_commands_disable_property_filtering() {
        let mut bytes = fixture(false).data().to_vec();
        bytes.truncate(bytes.len() - 3); // Replace the fixture's final stop command.
        command(&mut bytes, pbdems2::demo::command::SEND_TABLES, 30, &[]);
        command(&mut bytes, dem::STOP, 31, &[]);
        let parser = Parser::from_bytes(bytes);
        assert!(
            parser
                .property_filter(vec![("missing", Vec::new())])
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn unselected_event_datasets_remain_empty_in_parallel_collection() {
        let parser = fixture(false);
        let selection = EventDatasetSelection {
            kills: true,
            ..Default::default()
        };
        let part = parser.event_datasets_selected(selection).unwrap();
        assert!(part.shots.is_empty());
    }
}
