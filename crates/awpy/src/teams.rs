//! Team number to name mapping for Counter-Strike 2.
//!
//! Values are Source's `Team_t` numbers as used by the `m_iTeamNum` network
//! field and CS game events:
//!
//! ```text
//! 0 = TEAM_UNASSIGNED (none / still connecting)
//! 1 = TEAM_SPECTATOR
//! 2 = TEAM_TERRORIST            (T)
//! 3 = TEAM_CT                   (Counter-Terrorist)
//! ```

/// All known team (number, name) pairs sorted by number.
const TEAMS: &[(i64, &str)] = &[
    (0, "unassigned"),
    (1, "spectator"),
    (2, "terrorist"),
    (3, "counter-terrorist"),
];

/// Look up a team name by number. Returns `"TEAM_NOT_FOUND"` for unknown numbers.
pub fn team_name(id: i64) -> &'static str {
    TEAMS
        .iter()
        .find(|&&(k, _)| k == id)
        .map(|&(_, v)| v)
        .unwrap_or("TEAM_NOT_FOUND")
}

/// Return all known (team number, team name) pairs.
pub fn all_teams() -> &'static [(i64, &'static str)] {
    TEAMS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_teams() {
        assert_eq!(team_name(0), "unassigned");
        assert_eq!(team_name(1), "spectator");
        assert_eq!(team_name(2), "terrorist");
        assert_eq!(team_name(3), "counter-terrorist");
    }

    #[test]
    fn unknown_team() {
        assert_eq!(team_name(99), "TEAM_NOT_FOUND");
    }

    #[test]
    fn all_teams_count() {
        assert_eq!(all_teams().len(), 4);
    }
}
