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

/// Look up a team name by ID. Returns `"TEAM_NOT_FOUND"` for unknown IDs.
pub fn team_name(id: i64) -> &'static str {
    crate::find_name(TEAMS, id).unwrap_or("TEAM_NOT_FOUND")
}

/// Return all known (team ID, name) pairs.
pub fn all_teams() -> &'static [(i64, &'static str)] {
    TEAMS
}
