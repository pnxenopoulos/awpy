//! Hit group ID to name mapping for Counter-Strike 2.
//!
//! Values are Source 2's `HitGroup_t` enum, as reported by the `hitgroup`
//! key of the `player_hurt` game event:
//!
//! ```text
//! enum HitGroup_t
//! {
//!     HITGROUP_INVALID  = -1,
//!     HITGROUP_GENERIC  = 0,
//!     HITGROUP_HEAD     = 1,
//!     HITGROUP_CHEST    = 2,
//!     HITGROUP_STOMACH  = 3,
//!     HITGROUP_LEFTARM  = 4,
//!     HITGROUP_RIGHTARM = 5,
//!     HITGROUP_LEFTLEG  = 6,
//!     HITGROUP_RIGHTLEG = 7,
//!     HITGROUP_NECK     = 8,
//!     HITGROUP_UNUSED   = 9,
//!     HITGROUP_GEAR     = 10,
//!     HITGROUP_SPECIAL  = 11,
//! };
//! ```

/// All known hit group (ID, name) pairs sorted by ID.
const HITGROUPS: &[(i64, &str)] = &[
    (-1, "invalid"),
    (0, "generic"),
    (1, "head"),
    (2, "chest"),
    (3, "stomach"),
    (4, "left_arm"),
    (5, "right_arm"),
    (6, "left_leg"),
    (7, "right_leg"),
    (8, "neck"),
    (9, "unused"),
    (10, "gear"),
    (11, "special"),
];

/// Look up a hit group name by ID. Returns `"HITGROUP_NOT_FOUND"` for unknown IDs.
pub fn hitgroup_name(id: i64) -> &'static str {
    HITGROUPS
        .iter()
        .find(|&&(key, _)| key == id)
        .map_or("HITGROUP_NOT_FOUND", |&(_, value)| value)
}

/// Return all known (hit group ID, hit group name) pairs.
pub fn all_hitgroups() -> &'static [(i64, &'static str)] {
    HITGROUPS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_hitgroups() {
        assert_eq!(hitgroup_name(-1), "invalid");
        assert_eq!(hitgroup_name(0), "generic");
        assert_eq!(hitgroup_name(1), "head");
        assert_eq!(hitgroup_name(9), "unused");
        assert_eq!(hitgroup_name(10), "gear");
        assert_eq!(hitgroup_name(11), "special");
    }

    #[test]
    fn unknown_hitgroup() {
        assert_eq!(hitgroup_name(99), "HITGROUP_NOT_FOUND");
    }

    #[test]
    fn all_hitgroups_count() {
        assert_eq!(all_hitgroups().len(), 13);
    }
}
