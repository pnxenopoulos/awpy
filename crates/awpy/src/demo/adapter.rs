use std::collections::{HashMap, HashSet};

use awpy_proto::proto::{
    CDemoClassInfo, CDemoFullPacket, CDemoPacket, CDemoSendTables, CMsgSource1LegacyGameEvent,
    CMsgSource1LegacyGameEventList, CsvcMsgCreateStringTable, CsvcMsgFlattenedSerializer,
    CsvcMsgPacketEntities, CsvcMsgServerInfo, CsvcMsgUpdateStringTable, CsvcMsgUserMessage,
};
use pbdems2::demo::{CommandFrame, command as demo_command};
use pbdems2::entity::{
    BareCharEncoding, ClassEntry, CreateStringTable, DecodeProfile, FlattenedField,
    FlattenedSerializer, FlattenedSerializerDefinition, PacketEntities, PreciseQAngleMode,
    StringTableEntry, UpdateStringTable,
};
use pbdems2::io::ByteReader;
use pbdems2::{CheckpointAdapter, CommandContext, DemoAdapter};
use prost::Message;

use crate::error::{Error, Result};

use super::command::{self as awpy_command, ge, svc};
use super::parser::GameEvent;

const SYMBOLIC_ARRAY_LENGTHS: &[(&str, usize)] = &[
    ("MAX_ABILITY_DRAFT_ABILITIES", 48),
    ("DOTA_ABILITY_DRAFT_HEROES_PER_GAME", 10),
];
const POINTER_TYPES: &[&str] = &["CBodyComponentDCGBaseAnimating"];
const DYNAMIC_SERIALIZER_TYPES: &[&str] = &["m_SpeechBubbles", "DOTA_CombatLogQueryProgress"];

const DECODE_PROFILE: DecodeProfile = DecodeProfile::new(
    BareCharEncoding::NullTerminatedString,
    PreciseQAngleMode::Centered,
)
.with_ammo_field("m_iClip1")
.with_symbolic_array_lengths(SYMBOLIC_ARRAY_LENGTHS)
.with_pointer_types(POINTER_TYPES)
.with_dynamic_serializer_types(DYNAMIC_SERIALIZER_TYPES);

#[derive(Clone)]
pub(super) struct EventDescriptor {
    name: String,
    field_names: Vec<String>,
}

#[derive(Default)]
enum EventCollection {
    #[default]
    None,
    All,
    Legacy {
        names: HashSet<String>,
        event_ids: HashSet<i32>,
        include_payload: bool,
    },
}

/// The cheap subset of a legacy event needed to decide whether to decode it.
/// Prost skips the repeated key messages because they are not represented here.
#[derive(Clone, PartialEq, Message)]
struct LegacyEventIdentity {
    #[prost(string, optional, tag = "1")]
    event_name: Option<String>,
    #[prost(int32, optional, tag = "2")]
    event_id: Option<i32>,
}

#[derive(Default)]
pub(super) struct Cs2Adapter {
    packet_body: Vec<u8>,
    descriptors: HashMap<i32, EventDescriptor>,
    tick_events: Vec<GameEvent>,
    event_collection: EventCollection,
}

impl DemoAdapter for Cs2Adapter {
    type Error = Error;

    fn handle_command(
        &mut self,
        frame: &CommandFrame<'_>,
        body: &[u8],
        context: &mut CommandContext<'_, '_>,
    ) -> Result<()> {
        match frame.header().cmd {
            demo_command::SEND_TABLES => {
                let command = CDemoSendTables::decode(body)?;
                context.install_serializers(decode_send_tables(command)?, DECODE_PROFILE)?;
            }
            demo_command::CLASS_INFO => {
                let command = CDemoClassInfo::decode(body)?;
                context.install_class_info(command.classes.into_iter().map(|class| {
                    ClassEntry::new(
                        class.class_id.unwrap_or_default(),
                        class.network_name.unwrap_or_default(),
                        class.table_name.unwrap_or_default(),
                    )
                }))?;
            }
            demo_command::PACKET | demo_command::SIGNON_PACKET => {
                let command = CDemoPacket::decode(body)?;
                self.handle_packet(
                    command.data.as_deref().unwrap_or_default(),
                    frame.header().tick,
                    context,
                )?;
            }
            demo_command::FULL_PACKET => {
                let command = CDemoFullPacket::decode(body)?;
                if let Some(tables) = command.string_table {
                    context.apply_full_string_tables(tables.tables.into_iter().map(|table| {
                        let entries = table
                            .items
                            .into_iter()
                            .map(|item| StringTableEntry::new(item.str, item.data))
                            .collect();
                        (table.table_name.unwrap_or_default(), entries)
                    }))?;
                }
                if let Some(packet) = command.packet {
                    self.handle_packet(
                        packet.data.as_deref().unwrap_or_default(),
                        frame.header().tick,
                        context,
                    )?;
                }
            }
            _ => {}
        }
        Ok(())
    }
}

impl CheckpointAdapter for Cs2Adapter {
    type Checkpoint = HashMap<i32, EventDescriptor>;

    fn checkpoint(&self) -> Self::Checkpoint {
        self.descriptors.clone()
    }

    fn from_checkpoint(checkpoint: &Self::Checkpoint) -> Self {
        Self {
            descriptors: checkpoint.clone(),
            ..Self::default()
        }
    }
}

impl Cs2Adapter {
    pub(super) fn enable_events(&mut self) {
        self.event_collection = EventCollection::All;
    }

    pub(super) fn enable_legacy_events<'a>(
        &mut self,
        event_names: impl IntoIterator<Item = &'a str>,
        include_payload: bool,
    ) {
        let names: HashSet<String> = event_names.into_iter().map(str::to_owned).collect();
        let event_ids = self
            .descriptors
            .iter()
            .filter_map(|(&event_id, descriptor)| {
                names.contains(descriptor.name.as_str()).then_some(event_id)
            })
            .collect();
        self.event_collection = EventCollection::Legacy {
            names,
            event_ids,
            include_payload,
        };
    }

    pub(super) fn tick_events(&self) -> &[GameEvent] {
        &self.tick_events
    }

    pub(super) fn clear_tick_events(&mut self) {
        self.tick_events.clear();
    }

    fn collects_legacy_events(&self) -> bool {
        !matches!(self.event_collection, EventCollection::None)
    }

    fn collects_user_messages(&self) -> bool {
        matches!(self.event_collection, EventCollection::All)
    }

    /// Return whether a selected legacy event needs its raw protobuf payload.
    /// A missing result means the event is not selected.
    fn selected_legacy_event(&self, payload: &[u8]) -> Result<Option<bool>> {
        match &self.event_collection {
            EventCollection::None => Ok(None),
            EventCollection::All => Ok(Some(true)),
            EventCollection::Legacy {
                names,
                event_ids,
                include_payload,
            } => {
                let identity = LegacyEventIdentity::decode(payload)?;
                let selected = identity.event_id.is_some_and(|id| event_ids.contains(&id))
                    || identity
                        .event_name
                        .as_deref()
                        .is_some_and(|name| names.contains(name));
                Ok(selected.then_some(*include_payload))
            }
        }
    }

    fn handle_packet(
        &mut self,
        data: &[u8],
        tick: i32,
        context: &mut CommandContext<'_, '_>,
    ) -> Result<()> {
        for message in context.packet_messages(data) {
            let message = message?;
            let message_type = message.message_type();
            let is_entity_message = matches!(
                message_type,
                svc::CREATE_STRING_TABLE
                    | svc::UPDATE_STRING_TABLE
                    | svc::SERVER_INFO
                    | svc::PACKET_ENTITIES
            );
            let is_descriptor = message_type == ge::SOURCE1_LEGACY_GAME_EVENT_LIST;
            let is_user_message = message_type == svc::USER_MESSAGE
                || awpy_command::is_user_message_type(message_type);
            let is_collected_event = (message_type == ge::SOURCE1_LEGACY_GAME_EVENT
                && self.collects_legacy_events())
                || (is_user_message && self.collects_user_messages());
            if !(is_entity_message || is_descriptor || is_collected_event) {
                continue;
            }

            let payload = if let Some(payload) = message.payload() {
                payload
            } else {
                message.copy_payload(&mut self.packet_body)?;
                &self.packet_body
            };

            match message_type {
                svc::CREATE_STRING_TABLE => {
                    let message = CsvcMsgCreateStringTable::decode(payload)?;
                    context.create_string_table(create_string_table(message))?;
                }
                svc::UPDATE_STRING_TABLE => {
                    let message = CsvcMsgUpdateStringTable::decode(payload)?;
                    context.update_string_table(UpdateStringTable::new(
                        message.table_id.unwrap_or_default(),
                        message.num_changed_entries.unwrap_or_default(),
                        message.string_data.unwrap_or_default(),
                    ))?;
                }
                svc::SERVER_INFO => {
                    let message = CsvcMsgServerInfo::decode(payload)?;
                    if let Some(tick_interval) = message.tick_interval {
                        context.set_tick_interval(tick_interval)?;
                    }
                }
                svc::PACKET_ENTITIES => {
                    let message = CsvcMsgPacketEntities::decode(payload)?;
                    context.apply_packet_entities(PacketEntities::new(
                        message.updated_entries.unwrap_or_default(),
                        message.entity_data.as_deref().unwrap_or_default(),
                        message.has_pvs_vis_bits_deprecated.unwrap_or_default(),
                    ))?;
                }
                ge::SOURCE1_LEGACY_GAME_EVENT_LIST => {
                    let message = CMsgSource1LegacyGameEventList::decode(payload)?;
                    for descriptor in message.descriptors {
                        let event_id = descriptor.eventid.unwrap_or_default();
                        let name = descriptor.name.unwrap_or_default();
                        let selected = matches!(
                            &self.event_collection,
                            EventCollection::Legacy { names, .. }
                                if names.contains(name.as_str())
                        );
                        let field_names = descriptor
                            .keys
                            .iter()
                            .map(|key| key.name.clone().unwrap_or_default())
                            .collect();
                        self.descriptors
                            .insert(event_id, EventDescriptor { name, field_names });
                        if selected
                            && let EventCollection::Legacy { event_ids, .. } =
                                &mut self.event_collection
                        {
                            event_ids.insert(event_id);
                        }
                    }
                }
                ge::SOURCE1_LEGACY_GAME_EVENT if self.collects_legacy_events() => {
                    let Some(include_payload) = self.selected_legacy_event(payload)? else {
                        continue;
                    };
                    let message = CMsgSource1LegacyGameEvent::decode(payload)?;
                    let event_id = message.eventid.unwrap_or_default();
                    let (name, keys) = if let Some(descriptor) = self.descriptors.get(&event_id) {
                        let keys = descriptor
                            .field_names
                            .iter()
                            .zip(message.keys.iter())
                            .map(|(name, key)| (name.clone(), format_event_key(key)))
                            .collect();
                        (descriptor.name.clone(), keys)
                    } else {
                        (
                            message
                                .event_name
                                .unwrap_or_else(|| format!("event_{event_id}")),
                            Vec::new(),
                        )
                    };
                    self.tick_events.push(GameEvent {
                        tick,
                        name,
                        msg_type: message_type,
                        keys,
                        payload: if include_payload {
                            payload.to_vec()
                        } else {
                            Vec::new()
                        },
                    });
                }
                svc::USER_MESSAGE if self.collects_user_messages() => {
                    let message = CsvcMsgUserMessage::decode(payload)?;
                    let inner_type = message.msg_type.unwrap_or_default();
                    let msg_type = u32::try_from(inner_type).map_err(|_| Error::Parse {
                        context: format!("negative user message type: {inner_type}"),
                    })?;
                    self.tick_events.push(GameEvent {
                        tick,
                        name: awpy_command::user_message_name(inner_type),
                        msg_type,
                        keys: Vec::new(),
                        payload: message.msg_data.unwrap_or_default(),
                    });
                }
                direct_type
                    if self.collects_user_messages()
                        && awpy_command::is_user_message_type(direct_type) =>
                {
                    self.tick_events.push(GameEvent {
                        tick,
                        name: awpy_command::user_message_name(
                            i32::try_from(direct_type).expect("known user message type"),
                        ),
                        msg_type: direct_type,
                        keys: Vec::new(),
                        payload: payload.to_vec(),
                    });
                }
                _ => unreachable!(),
            }
        }
        Ok(())
    }
}

fn format_event_key(key: &awpy_proto::proto::c_msg_source1_legacy_game_event::KeyT) -> String {
    if let Some(ref value) = key.val_string {
        return value.clone();
    }
    if let Some(value) = key.val_float {
        return value.to_string();
    }
    if let Some(value) = key.val_long {
        return value.to_string();
    }
    if let Some(value) = key.val_short {
        return value.to_string();
    }
    if let Some(value) = key.val_byte {
        return value.to_string();
    }
    if let Some(value) = key.val_bool {
        return value.to_string();
    }
    if let Some(value) = key.val_uint64 {
        return value.to_string();
    }
    String::new()
}

fn decode_send_tables(command: CDemoSendTables) -> Result<FlattenedSerializer> {
    let data = command.data.unwrap_or_default();
    let mut reader = ByteReader::new(&data);
    let _encoded_size = reader.read_uvarint64()?;
    let remaining = reader.read_bytes(reader.remaining())?;
    let message = CsvcMsgFlattenedSerializer::decode(remaining)?;

    Ok(FlattenedSerializer::new(
        message
            .serializers
            .into_iter()
            .map(|serializer| {
                FlattenedSerializerDefinition::new(
                    serializer.serializer_name_sym,
                    serializer.fields_index,
                )
            })
            .collect(),
        message.symbols,
        message
            .fields
            .into_iter()
            .map(|field| {
                FlattenedField::new(field.var_type_sym, field.var_name_sym)
                    .with_bit_count(field.bit_count)
                    .with_range(field.low_value, field.high_value)
                    .with_encode_flags(field.encode_flags)
                    .with_serializer_name_sym(field.field_serializer_name_sym)
                    .with_send_node_sym(field.send_node_sym)
                    .with_encoder_sym(field.var_encoder_sym)
                    .with_polymorphic(!field.polymorphic_types.is_empty())
            })
            .collect(),
    ))
}

fn create_string_table(message: CsvcMsgCreateStringTable) -> CreateStringTable {
    let mut table = CreateStringTable::new(
        message.name.unwrap_or_default(),
        message.num_entries.unwrap_or_default(),
        message.string_data.unwrap_or_default(),
    )
    .with_flags(message.flags.unwrap_or_default());
    if message.user_data_fixed_size.unwrap_or_default() {
        table = table.with_fixed_user_data(
            message.user_data_size.unwrap_or_default(),
            message.user_data_size_bits.unwrap_or_default(),
        );
    }
    if message.data_compressed.unwrap_or_default() {
        table = table.with_compressed_data();
    }
    if message.using_varint_bitcounts.unwrap_or_default() {
        table = table.with_varint_bitcounts();
    }
    table
}

#[cfg(test)]
mod tests {
    use awpy_proto::proto::c_msg_source1_legacy_game_event::KeyT;

    use super::*;

    fn legacy_event(event_id: i32, event_name: Option<&str>) -> Vec<u8> {
        CMsgSource1LegacyGameEvent {
            event_name: event_name.map(str::to_owned),
            eventid: Some(event_id),
            keys: vec![KeyT {
                val_string: Some("discarded for an unselected event".to_string()),
                ..Default::default()
            }],
            ..Default::default()
        }
        .encode_to_vec()
    }

    #[test]
    fn selective_events_match_descriptor_ids_without_payloads() {
        let mut adapter = Cs2Adapter::default();
        adapter.descriptors.insert(
            7,
            EventDescriptor {
                name: "player_death".to_string(),
                field_names: Vec::new(),
            },
        );
        adapter.enable_legacy_events(["player_death"], false);

        assert_eq!(
            adapter
                .selected_legacy_event(&legacy_event(7, None))
                .unwrap(),
            Some(false)
        );
        assert_eq!(
            adapter
                .selected_legacy_event(&legacy_event(8, None))
                .unwrap(),
            None
        );
        assert!(!adapter.collects_user_messages());
    }

    #[test]
    fn selective_events_fall_back_to_embedded_names() {
        let mut adapter = Cs2Adapter::default();
        adapter.enable_legacy_events(["weapon_fire"], false);

        assert_eq!(
            adapter
                .selected_legacy_event(&legacy_event(99, Some("weapon_fire")))
                .unwrap(),
            Some(false)
        );
    }

    #[test]
    fn full_event_collection_keeps_payloads_and_user_messages() {
        let mut adapter = Cs2Adapter::default();
        adapter.enable_events();

        assert_eq!(
            adapter
                .selected_legacy_event(&legacy_event(7, None))
                .unwrap(),
            Some(true)
        );
        assert!(adapter.collects_user_messages());
    }
}
