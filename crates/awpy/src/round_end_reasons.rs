//! Round-end reason ID to name mapping for Counter-Strike 2.
//!
//! Values are Source's `RoundEndReason_t`, as reported by the `reason` key of
//! the `round_end` game event. (Several reasons — the VIP and escape modes —
//! are legacy and never occur in modern competitive CS2, but are included for
//! completeness.)

/// All known round-end reason (ID, name) pairs sorted by ID.
const ROUND_END_REASONS: &[(i64, &str)] = &[
    (0, "still_in_progress"),
    (1, "target_bombed"),
    (2, "vip_escaped"),
    (3, "vip_killed"),
    (4, "terrorists_escaped"),
    (5, "ct_stopped_escape"),
    (6, "terrorists_stopped"),
    (7, "bomb_defused"),
    (8, "ct_win"),
    (9, "terrorists_win"),
    (10, "draw"),
    (11, "hostages_rescued"),
    (12, "target_saved"),
    (13, "hostages_not_rescued"),
    (14, "terrorists_not_escaped"),
    (15, "vip_not_escaped"),
    (16, "game_start"),
    (17, "terrorists_surrender"),
    (18, "ct_surrender"),
    (19, "terrorists_planted"),
    (20, "cts_reached_hostage"),
];

/// Look up a round-end reason name by ID. Returns `"ROUND_END_REASON_NOT_FOUND"`
/// for unknown IDs.
pub fn round_end_reason_name(id: i64) -> &'static str {
    ROUND_END_REASONS
        .iter()
        .find(|&&(k, _)| k == id)
        .map(|&(_, v)| v)
        .unwrap_or("ROUND_END_REASON_NOT_FOUND")
}

/// Return all known (round-end reason ID, name) pairs.
pub fn all_round_end_reasons() -> &'static [(i64, &'static str)] {
    ROUND_END_REASONS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_reasons() {
        assert_eq!(round_end_reason_name(1), "target_bombed");
        assert_eq!(round_end_reason_name(7), "bomb_defused");
        assert_eq!(round_end_reason_name(8), "ct_win");
        assert_eq!(round_end_reason_name(9), "terrorists_win");
    }

    #[test]
    fn unknown_reason() {
        assert_eq!(round_end_reason_name(99), "ROUND_END_REASON_NOT_FOUND");
    }

    #[test]
    fn all_reasons_count() {
        assert_eq!(all_round_end_reasons().len(), 21);
    }
}
