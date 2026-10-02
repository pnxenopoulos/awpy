use prost::Message;

/// Helper macro: expands to a `match` that tries `prost::Message::decode`
/// for each `(msg_type => ProtoType)` pair and pretty-prints the result.
macro_rules! decode_match {
    ($msg_type:expr, $data:expr, $($val:expr => $ty:ty),* $(,)?) => {
        match $msg_type {
            $($val => <$ty>::decode($data).ok().map(|m| format!("{:#?}", m)),)*
            _ => None,
        }
    }
}

/// Attempt to decode raw protobuf bytes for a known user-message type.
///
/// `msg_type` is an `ECstrike15UserMessages` (`CS_UM_*`) or
/// `EBaseUserMessages` (`UM_*`) ID. A packet can store the message directly or
/// inside `svc_UserMessage`.
/// Returns `Some(pretty-printed string)` when the type is recognized and the
/// payload decodes, or `None` otherwise. Only a curated set of commonly useful
/// messages is mapped; unmapped types return `None`.
pub fn decode_event_payload(msg_type: u32, data: &[u8]) -> Option<String> {
    use awpy_proto::proto::*;

    decode_match!(msg_type, data,
        // ── ECstrike15UserMessages (CS_UM_*) ──
        304 => CcsUsrMsgHudText,
        305 => CUserMessageSayText,
        306 => CUserMessageSayText2,
        308 => CcsUsrMsgHudMsg,
        312 => CcsUsrMsgShake,
        313 => CcsUsrMsgFade,
        315 => CcsUsrMsgCloseCaption,
        321 => CcsUsrMsgDamage,
        322 => CcsUsrMsgRadioText,
        323 => CcsUsrMsgHintText,
        325 => CcsUsrMsgProcessSpottedEntityUpdate,
        327 => CcsUsrMsgAdjustMoney,
        333 => CcsUsrMsgAchievementEvent,
        334 => CcsUsrMsgMatchEndConditions,
        336 => CcsUsrMsgPlayerStatsUpdate,
        339 => CcsUsrMsgClientInfo,
        353 => CcsUsrMsgItemPickup,
        355 => CcsUsrMsgBarTime,
        356 => CcsUsrMsgAmmoDenied,
        357 => CcsUsrMsgMarkAchievement,
        358 => CcsUsrMsgMatchStatsUpdate,
        359 => CcsUsrMsgItemDrop,
        366 => CcsUsrMsgQuestProgress,
        368 => CcsUsrMsgPlayerDecalDigitalSignature,
        371 => CcsUsrMsgEntityOutlineHighlight,
        375 => CcsUsrMsgEndOfMatchAllPlayersData,
        376 => CcsUsrMsgPostRoundDamageReport,
        380 => CcsUsrMsgCurrentRoundOdds,
        381 => CcsUsrMsgDeepStats,
        385 => CcsUsrMsgCounterStrafe,
        386 => CcsUsrMsgDamagePrediction,

        // ── EBaseUserMessages (UM_*) ──
        117 => CUserMessageSayText,
        118 => CUserMessageSayText2,
        119 => CUserMessageSayTextChannel,
        124 => CUserMessageTextMsg,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_msg_type_returns_none() {
        assert!(decode_event_payload(0, &[]).is_none());
        assert!(decode_event_payload(9999, &[1, 2, 3]).is_none());
    }

    #[test]
    fn known_type_empty_bytes_returns_some() {
        // Empty bytes decode as an empty protobuf message. 308 is CS_UM_HudMsg.
        let result = decode_event_payload(308, &[]);
        assert!(result.is_some());
    }

    #[test]
    fn known_type_invalid_bytes_no_panic() {
        // Garbage bytes may or may not decode; just ensure no panic.
        let _ = decode_event_payload(321, &[0xFF, 0xFF, 0xFF, 0xFF]);
    }
}
