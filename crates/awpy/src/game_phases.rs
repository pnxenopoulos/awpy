//! Game-phase ID to name mapping for Counter-Strike 2.
//!
//! Values are the game rules' `m_gamePhase` field (`GamePhase` enum):
//!
//! ```text
//! 0 = init
//! 1 = pregame (warmup)
//! 2 = start game phase
//! 3 = team side switch / pre-round
//! 4 = game half ended
//! 5 = game ended / restart
//! 6 = stalemate
//! 7 = game over
//! ```

/// All known game-phase (ID, name) pairs sorted by ID.
const GAME_PHASES: &[(i64, &str)] = &[
    (0, "init"),
    (1, "pregame"),
    (2, "start_game_phase"),
    (3, "team_side_switch"),
    (4, "game_half_ended"),
    (5, "game_ended"),
    (6, "stalemate"),
    (7, "game_over"),
];

/// Look up a game-phase name by ID. Returns `"GAME_PHASE_NOT_FOUND"` for unknown IDs.
pub fn game_phase_name(id: i64) -> &'static str {
    GAME_PHASES
        .iter()
        .find(|&&(key, _)| key == id)
        .map_or("GAME_PHASE_NOT_FOUND", |&(_, value)| value)
}

/// Return all known (game-phase ID, name) pairs.
pub fn all_game_phases() -> &'static [(i64, &'static str)] {
    GAME_PHASES
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_phases() {
        assert_eq!(game_phase_name(0), "init");
        assert_eq!(game_phase_name(1), "pregame");
        assert_eq!(game_phase_name(7), "game_over");
    }

    #[test]
    fn unknown_phase() {
        assert_eq!(game_phase_name(99), "GAME_PHASE_NOT_FOUND");
    }

    #[test]
    fn all_phases_count() {
        assert_eq!(all_game_phases().len(), 8);
    }
}
