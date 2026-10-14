//! Event decoding shared by the event scan and entity playback.

use std::collections::HashMap;

use awpy_proto::proto::{
    CMsgSource1LegacyGameEvent, CsvcMsgUserMessage, c_msg_source1_legacy_game_event::KeyT,
    c_msg_source1_legacy_game_event_list::DescriptorT,
};
use prost::Message;

use crate::error::{Error, Result};

use super::command;
use super::parser::GameEvent;

#[derive(Clone)]
pub(super) struct EventDescriptor {
    pub(super) name: String,
    pub(super) field_names: Vec<String>,
}

impl From<DescriptorT> for EventDescriptor {
    fn from(descriptor: DescriptorT) -> Self {
        Self {
            name: descriptor.name.unwrap_or_default(),
            field_names: descriptor
                .keys
                .into_iter()
                .map(|key| key.name.unwrap_or_default())
                .collect(),
        }
    }
}

pub(super) fn decode_legacy_event(
    tick: i32,
    msg_type: u32,
    payload: &[u8],
    descriptors: &HashMap<i32, EventDescriptor>,
    include_payload: bool,
) -> Result<GameEvent> {
    let message = CMsgSource1LegacyGameEvent::decode(payload)?;
    let event_id = message.eventid.unwrap_or_default();
    let (name, keys) = if let Some(descriptor) = descriptors.get(&event_id) {
        let keys = descriptor
            .field_names
            .iter()
            .zip(message.keys)
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
    Ok(GameEvent {
        tick,
        name,
        msg_type,
        keys,
        payload: if include_payload {
            payload.to_vec()
        } else {
            Vec::new()
        },
    })
}

pub(super) fn decode_user_message(tick: i32, payload: &[u8]) -> Result<GameEvent> {
    let message = CsvcMsgUserMessage::decode(payload)?;
    let inner_type = message.msg_type.unwrap_or_default();
    let msg_type = u32::try_from(inner_type).map_err(|_| Error::Parse {
        context: format!("negative user message type: {inner_type}"),
    })?;
    Ok(GameEvent {
        tick,
        name: command::user_message_name(inner_type),
        msg_type,
        keys: Vec::new(),
        payload: message.msg_data.unwrap_or_default(),
    })
}

pub(super) fn decode_direct_user_message(
    tick: i32,
    msg_type: u32,
    payload: &[u8],
) -> Result<GameEvent> {
    let inner_type = i32::try_from(msg_type).map_err(|_| Error::Parse {
        context: format!("user message type out of range: {msg_type}"),
    })?;
    Ok(GameEvent {
        tick,
        name: command::user_message_name(inner_type),
        msg_type,
        keys: Vec::new(),
        payload: payload.to_vec(),
    })
}

/// Keep the protobuf field order when more than one value is present.
fn format_event_key(key: KeyT) -> String {
    if let Some(value) = key.val_string {
        return value;
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

#[cfg(test)]
mod tests {
    use super::super::command::ge;
    use super::*;

    #[test]
    fn legacy_values_keep_their_text_and_descriptor_order() {
        let values = vec![
            KeyT {
                val_string: Some("text".into()),
                val_long: Some(99),
                ..Default::default()
            },
            KeyT {
                val_float: Some(1.25),
                ..Default::default()
            },
            KeyT {
                val_long: Some(-123),
                ..Default::default()
            },
            KeyT {
                val_short: Some(-2),
                ..Default::default()
            },
            KeyT {
                val_byte: Some(255),
                ..Default::default()
            },
            KeyT {
                val_bool: Some(false),
                ..Default::default()
            },
            KeyT {
                val_uint64: Some(u64::MAX),
                ..Default::default()
            },
            KeyT::default(),
        ];
        let names: Vec<String> = (0..values.len())
            .map(|index| format!("key_{index}"))
            .collect();
        let descriptors = HashMap::from([(
            7,
            EventDescriptor {
                name: "player_death".into(),
                field_names: names.clone(),
            },
        )]);
        let payload = CMsgSource1LegacyGameEvent {
            eventid: Some(7),
            event_name: Some("ignored_name".into()),
            keys: values,
            ..Default::default()
        }
        .encode_to_vec();
        let event = decode_legacy_event(
            42,
            ge::SOURCE1_LEGACY_GAME_EVENT,
            &payload,
            &descriptors,
            true,
        )
        .unwrap();
        let expected = [
            "text",
            "1.25",
            "-123",
            "-2",
            "255",
            "false",
            "18446744073709551615",
            "",
        ];
        assert_eq!(event.name, "player_death");
        assert_eq!(event.tick, 42);
        assert_eq!(event.msg_type, ge::SOURCE1_LEGACY_GAME_EVENT);
        assert_eq!(
            event.keys,
            names
                .into_iter()
                .zip(expected.map(str::to_owned))
                .collect::<Vec<_>>()
        );
        assert_eq!(event.payload, payload);

        let selected = decode_legacy_event(
            42,
            ge::SOURCE1_LEGACY_GAME_EVENT,
            &payload,
            &descriptors,
            false,
        )
        .unwrap();
        assert_eq!(selected.keys, event.keys);
        assert!(selected.payload.is_empty());
    }

    #[test]
    fn unknown_events_use_the_embedded_name_or_numeric_fallback() {
        for (name, expected) in [(Some("custom"), "custom"), (None, "event_9")] {
            let payload = CMsgSource1LegacyGameEvent {
                eventid: Some(9),
                event_name: name.map(str::to_owned),
                keys: vec![KeyT::default()],
                ..Default::default()
            }
            .encode_to_vec();
            let event = decode_legacy_event(
                1,
                ge::SOURCE1_LEGACY_GAME_EVENT,
                &payload,
                &HashMap::new(),
                false,
            )
            .unwrap();
            assert_eq!(event.name, expected);
            assert!(event.keys.is_empty());
        }
    }

    #[test]
    fn wrapped_and_direct_user_messages_have_the_same_content() {
        let payload = b"chat payload";
        let wrapped = CsvcMsgUserMessage {
            msg_type: Some(118),
            msg_data: Some(payload.to_vec()),
            ..Default::default()
        }
        .encode_to_vec();
        let event = decode_user_message(50, &wrapped).unwrap();
        let direct = decode_direct_user_message(50, 118, payload).unwrap();
        assert_eq!(event.tick, direct.tick);
        assert_eq!(event.name, direct.name);
        assert_eq!(event.msg_type, direct.msg_type);
        assert_eq!(event.payload, direct.payload);
        assert!(event.keys.is_empty());
        assert!(direct.keys.is_empty());
    }

    #[test]
    fn invalid_user_message_types_return_errors() {
        let payload = CsvcMsgUserMessage {
            msg_type: Some(-1),
            ..Default::default()
        }
        .encode_to_vec();
        assert!(decode_user_message(1, &payload).is_err());
        assert!(decode_direct_user_message(1, u32::MAX, &[]).is_err());
    }

    #[test]
    fn truncated_protobuf_events_return_errors() {
        assert!(decode_legacy_event(1, 1, &[0x80], &HashMap::new(), true).is_err());
        assert!(decode_user_message(1, &[0x80]).is_err());
    }
}
