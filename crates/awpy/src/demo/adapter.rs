use awpy_proto::proto::{
    CDemoClassInfo, CDemoFullPacket, CDemoPacket, CDemoSendTables, CsvcMsgCreateStringTable,
    CsvcMsgFlattenedSerializer, CsvcMsgPacketEntities, CsvcMsgServerInfo, CsvcMsgUpdateStringTable,
};
use pbdems2::demo::{CommandFrame, command};
use pbdems2::entity::{
    BareCharEncoding, ClassEntry, CreateStringTable, DecodeProfile, FlattenedField,
    FlattenedSerializer, FlattenedSerializerDefinition, PacketEntities, PreciseQAngleMode,
    StringTableEntry, UpdateStringTable,
};
use pbdems2::io::ByteReader;
use pbdems2::{CheckpointAdapter, CommandContext, DemoAdapter};
use prost::Message;

use crate::error::{Error, Result};

use super::command::svc;

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

#[derive(Default)]
pub(super) struct Cs2Adapter {
    packet_body: Vec<u8>,
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
            command::SEND_TABLES => {
                let command = CDemoSendTables::decode(body)?;
                context.install_serializers(decode_send_tables(command)?, DECODE_PROFILE)?;
            }
            command::CLASS_INFO => {
                let command = CDemoClassInfo::decode(body)?;
                context.install_class_info(command.classes.into_iter().map(|class| {
                    ClassEntry::new(
                        class.class_id.unwrap_or_default(),
                        class.network_name.unwrap_or_default(),
                        class.table_name.unwrap_or_default(),
                    )
                }))?;
            }
            command::PACKET | command::SIGNON_PACKET => {
                let command = CDemoPacket::decode(body)?;
                self.handle_packet(command.data.as_deref().unwrap_or_default(), context)?;
            }
            command::FULL_PACKET => {
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
                    self.handle_packet(packet.data.as_deref().unwrap_or_default(), context)?;
                }
            }
            _ => {}
        }
        Ok(())
    }
}

impl CheckpointAdapter for Cs2Adapter {
    type Checkpoint = ();

    fn checkpoint(&self) -> Self::Checkpoint {}

    fn from_checkpoint(_: &Self::Checkpoint) -> Self {
        Self::default()
    }
}

impl Cs2Adapter {
    fn handle_packet(&mut self, data: &[u8], context: &mut CommandContext<'_, '_>) -> Result<()> {
        for message in context.packet_messages(data) {
            let message = message?;
            let message_type = message.message_type();
            if !matches!(
                message_type,
                svc::CREATE_STRING_TABLE
                    | svc::UPDATE_STRING_TABLE
                    | svc::SERVER_INFO
                    | svc::PACKET_ENTITIES
            ) {
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
                _ => unreachable!(),
            }
        }
        Ok(())
    }
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
