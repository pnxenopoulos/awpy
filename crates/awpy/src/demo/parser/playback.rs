use std::collections::HashSet;

use pbdems2::{DemoParser, PlaybackSession, PreparedPlayback, PropertyFilter};

use crate::entity::{ClassInfo, SerializerContainer};
use crate::error::Result;

use super::super::adapter::MetadataUpdate;
use super::{Context, Cs2Adapter, DEFAULT_TICK_INTERVAL, GameEvent, HEADER_SIZE, Parser};
use crate::datasets::EventDatasetSelection;

/// Compact state needed before a cold keyframe: no entity snapshots are cached.
pub(crate) struct CombatBootstrap {
    updates: Vec<MetadataUpdate>,
    events: Vec<GameEvent>,
    pub(crate) class_schema_changed: bool,
}

/// A keyframe-bounded decode range: `(start, end_tick)`, where `start` is a
/// full-packet offset relative to the post-header stream, or `None` for the
/// signon baseline.
pub type Segment = (Option<usize>, i32);

/// Number of segments for a parallel pass: the CPU count, overridable via
/// `AWPY_TICK_SEGMENTS` (read fresh so a test can force the serial path with
/// `1`).
pub(crate) fn segment_budget() -> usize {
    std::env::var("AWPY_TICK_SEGMENTS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or_else(|| std::thread::available_parallelism().map_or(1, usize::from))
}

impl Parser {
    fn prepared(&self) -> Result<&PreparedPlayback<Cs2Adapter>> {
        self.prepared_cache.get_or_try_init(|| {
            DemoParser::new(self.data())?.prepare(Cs2Adapter::default(), DEFAULT_TICK_INTERVAL)
        })
    }

    /// A fresh playback run from the cached signon state.
    fn session(&self) -> Result<PlaybackSession<'_, '_, Cs2Adapter>> {
        self.prepared()?.session(DemoParser::new(self.data())?)
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
        self.session()?.parse_to_tick(target_tick)
    }

    /// Parse the entire demo, calling a callback once per completed tick.
    pub fn run_to_end<F>(&self, on_tick: F) -> Result<()>
    where
        F: FnMut(&Context),
    {
        self.session()?.run_to_end(on_tick)?;
        Ok(())
    }

    /// Parse the entire demo while materializing only selected entity classes.
    pub fn run_to_end_filtered<F>(&self, class_filter: &HashSet<&str>, on_tick: F) -> Result<()>
    where
        F: FnMut(&Context),
    {
        self.session()?.run_to_end_filtered(class_filter, on_tick)?;
        Ok(())
    }

    /// Parse entities and game events in one filtered pass.
    pub fn run_to_end_with_events_filtered<F>(
        &self,
        class_filter: &HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        let mut session = self.session()?;
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
        class_filter: &HashSet<&str>,
        event_names: &HashSet<&str>,
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
        self.combat_bootstrap.get_or_try_init(|| {
            let mut session = self.session()?;
            session.adapter_mut().metadata_only = true;
            session
                .adapter_mut()
                .enable_legacy_events(EventDatasetSelection::ALL.legacy_event_names(), false);
            let mut bootstrap = CombatBootstrap {
                updates: Vec::new(),
                events: Vec::new(),
                class_schema_changed: false,
            };
            session.run_to_end_filtered_with_adapter(&HashSet::new(), |_, adapter| {
                bootstrap.updates.append(&mut adapter.metadata_updates);
                bootstrap.events.append(&mut adapter.tick_events);
                bootstrap.class_schema_changed |= adapter.class_schema_changed;
            })?;
            Ok(bootstrap)
        })
    }

    /// Decode entities in a segment and join authoritative events by completed tick.
    /// Events before the full-packet command on its tick still belong to this segment.
    pub(crate) fn run_legacy_event_segment<F>(
        &self,
        class_filter: &HashSet<&str>,
        event_names: &HashSet<&str>,
        properties: Option<&PropertyFilter>,
        segment: Option<Segment>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        let mut session = match properties {
            Some(properties) => self
                .prepared()?
                .session_with_properties(DemoParser::new(self.data())?, properties.clone())?,
            None => self.session()?,
        };
        let Some((start, end_tick)) = segment else {
            session
                .adapter_mut()
                .enable_legacy_events(event_names.iter().copied(), false);
            session.run_to_end_filtered_with_adapter(class_filter, |state, adapter| {
                on_tick(state, adapter.tick_events());
                adapter.clear_tick_events();
            })?;
            return Ok(());
        };
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
                let events = &bootstrap.events;
                let begin = *cursor
                    .get_or_insert_with(|| events.partition_point(|e| e.tick < state.tick()));
                let end = begin + events[begin..].partition_point(|e| e.tick == state.tick());
                on_tick(state, &events[begin..end]);
                cursor = Some(end);
            },
        )?;
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
        class_filter: &HashSet<&str>,
        on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        self.session()?.decode_segment(
            start.map(|offset| offset + HEADER_SIZE),
            end_tick,
            class_filter,
            on_tick,
        )?;
        Ok(())
    }

    /// Run `f` across keyframe segments on scoped threads and return the
    /// results in tick order.
    ///
    /// `f` gets `None` once, on the calling thread, when `parallel` is false or
    /// the segment budget (see `AWPY_TICK_SEGMENTS`) is 1. Otherwise it gets
    /// each [`Segment`]: the first from the signon baseline, the rest
    /// cold-restarting at evenly spaced full packets.
    pub fn map_segments<T: Send>(
        &self,
        parallel: bool,
        f: impl Fn(Option<Segment>) -> Result<T> + Sync,
    ) -> Result<Vec<T>> {
        let budget = if parallel { segment_budget() } else { 1 };
        if budget <= 1 {
            return Ok(vec![f(None)?]);
        }
        let plan = self.prepared()?.segment_plan(budget);
        let f = &f;
        std::thread::scope(|scope| {
            let workers: Vec<_> = plan
                .iter()
                .map(|segment| {
                    let start = segment.start_offset().map(|offset| offset - HEADER_SIZE);
                    let end_tick = segment.end_tick();
                    scope.spawn(move || f(Some((start, end_tick))))
                })
                .collect();
            workers
                .into_iter()
                .map(|worker| worker.join().expect("segment worker panicked"))
                .collect()
        })
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

    /// Append the low `count` bits of `value`, least significant first.
    fn write_bits(bits: &mut Vec<bool>, value: u64, count: usize) {
        bits.extend((0..count).map(|i| (value >> i) & 1 != 0));
    }

    fn pack_bits(bits: &[bool]) -> Vec<u8> {
        let mut bytes = vec![0; bits.len().div_ceil(8)];
        for (i, &bit) in bits.iter().enumerate() {
            bytes[i / 8] |= u8::from(bit) << (i % 8);
        }
        bytes
    }

    fn packet(kind: u32, body: &[u8]) -> Vec<u8> {
        // A `ubitvar` message type: a 2-bit width tag over the low nibble, then the rest.
        let (tag, extra) = match kind {
            0..16 => (0, 0),
            16..256 => (16, 4),
            256..4096 => (32, 8),
            _ => (48, 28),
        };
        let mut bits = Vec::new();
        write_bits(&mut bits, u64::from((kind & 15) | tag), 6);
        write_bits(&mut bits, u64::from(kind >> 4), extra);
        let mut length = Vec::new();
        varint(body.len() as u64, &mut length);
        for &byte in length.iter().chain(body) {
            write_bits(&mut bits, u64::from(byte), 8);
        }
        CDemoPacket {
            data: Some(pack_bits(&bits)),
        }
        .encode_to_vec()
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
        for &byte in b"12\0" {
            write_bits(&mut bits, u64::from(byte), 8);
        }
        bits.push(true); // user data
        write_bits(&mut bits, 171, 8);
        let update = CsvcMsgUpdateStringTable {
            table_id: Some(0),
            num_changed_entries: Some(1),
            string_data: Some(pack_bits(&bits)),
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

    /// Decode the fixture's second keyframe segment.
    fn decode_second_segment(on_tick: impl FnMut(&Context, &[GameEvent])) {
        let parser = fixture(false);
        let start = parser.full_packet_offsets().unwrap()[1].0;
        let names = EventDatasetSelection::ALL.legacy_event_names();
        let segment = Some((Some(start), i32::MAX));
        parser
            .run_legacy_event_segment(&Default::default(), &names, None, segment, on_tick)
            .unwrap();
    }

    #[test]
    fn parallel_segments_restore_string_tables_created_after_signon() {
        let mut restored = false;
        decode_second_segment(|ctx, _| {
            restored = ctx.string_tables().find_table("instancebaseline").is_some();
        });
        assert!(restored);
    }

    #[test]
    fn parallel_segments_restore_late_class_baselines() {
        let mut baseline = None;
        decode_second_segment(|ctx, _| {
            baseline = ctx
                .string_tables()
                .instance_baseline(12)
                .map(<[u8]>::to_vec);
        });
        assert_eq!(baseline, Some(vec![171]));
    }

    #[test]
    fn events_before_a_keyframe_on_its_tick_keep_source_order() {
        let mut labels = Vec::new();
        decode_second_segment(|_, events| {
            labels.extend(events.iter().map(|event| event.keys[0].1.clone()));
        });
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
