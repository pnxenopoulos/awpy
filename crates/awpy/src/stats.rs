//! Aggregate player statistics computed from the kill, damage, and round
//! datasets.
//!
//! [`player_stats`] is a pure function over the datasets, so it is easy to test
//! and reuse; [`Parser::player_stats`] is the convenience entry point that
//! parses the demo and calls it with a trade window derived from the tick rate.
//!
//! Definitions (standard CS analytics conventions):
//! - **Opening kill / death** — the attacker / victim of the *first* kill of a
//!   round.
//! - **Traded death** — a death whose killer is themselves killed by a teammate
//!   of the victim within the trade window (default 5 seconds).
//! - **KAST** — percentage of rounds in which the player got a **K**ill,
//!   **A**ssist, **S**urvived, or was **T**raded.
//! - **ADR** — average damage per round, using the actual HP removed from
//!   enemies (each hit capped at the victim's remaining health, chained across
//!   the round, so a killing blow counts only what the victim had left),
//!   divided by rounds played. Team, self, and world damage are excluded.
//! - **Multi-kill rounds** — rounds with exactly 2 / 3 / 4 / 5+ kills.
//!
//! Player rosters are taken from everyone who appears in a kill or damage, and
//! every player is assumed to have played every round — the denominator for
//! KAST and ADR is the match's total round count. Players who join or leave
//! mid-match are therefore approximate.

use std::collections::{HashMap, HashSet};

use crate::datasets::{Blind, Damage, EventDatasets, Kill, Round, Shot};
use crate::demo::Parser;
use crate::error::Result;

/// Default trade window in seconds.
const TRADE_SECONDS: f32 = 5.0;
/// Fallback tick rate when the demo does not report playback timing.
const DEFAULT_TICKRATE: f32 = 64.0;

/// Aggregate statistics for a single player across a match.
#[derive(Debug, Clone, serde::Serialize)]
pub struct PlayerStats {
    pub steamid: u64,
    pub name: String,
    pub rounds_played: i32,
    pub kills: i32,
    pub deaths: i32,
    pub assists: i32,
    pub flash_assists: i32,
    pub headshot_kills: i32,
    /// Headshot kills as a percentage of kills (0 when the player has no kills).
    pub headshot_pct: f32,
    pub opening_kills: i32,
    pub opening_deaths: i32,
    pub traded_deaths: i32,
    /// Rounds with exactly 2 / 3 / 4 / 5-or-more kills.
    pub multikill_2k: i32,
    pub multikill_3k: i32,
    pub multikill_4k: i32,
    pub multikill_5k: i32,
    /// Kill / Assist / Survived / Traded percentage (0–100).
    pub kast: f32,
    /// Average damage per round.
    pub adr: f32,
    // ── Utility ──
    /// Grenade damage dealt to enemies (HE + molotov / incendiary), as actual HP
    /// removed (chained like ADR).
    pub utility_damage: i32,
    /// Flashbangs thrown.
    pub flashes_thrown: i32,
    /// Number of times an enemy was blinded by one of this player's flashes.
    pub enemies_flashed: i32,
    /// Total seconds of blindness this player inflicted on enemies.
    pub flash_duration_dealt: f32,
}

/// Per-player running totals, collapsed into [`PlayerStats`] at the end.
#[derive(Default)]
struct Acc {
    name: String,
    kills: i32,
    deaths: i32,
    assists: i32,
    flash_assists: i32,
    headshot_kills: i32,
    opening_kills: i32,
    opening_deaths: i32,
    traded_deaths: i32,
    damage: i32,
    utility_damage: i32,
    flashes_thrown: i32,
    enemies_flashed: i32,
    flash_duration_dealt: f32,
    /// Round index → number of kills that round.
    kill_rounds: HashMap<usize, i32>,
    assist_rounds: HashSet<usize>,
    death_rounds: HashSet<usize>,
    traded_rounds: HashSet<usize>,
}

/// Live start tick of each round (freeze start where known).
fn round_starts(rounds: &[Round]) -> Vec<i32> {
    rounds
        .iter()
        .map(|r| r.start_tick.or(r.freeze_end_tick).unwrap_or(r.end_tick))
        .collect()
}

/// Each round's freeze period as a half-open `[start_tick, freeze_end_tick)`
/// range, ascending.
///
/// Nobody can legitimately die while play is frozen, so anything the demo
/// reports here is an artifact and must not reach the stat tallies. Two
/// situations produce them, and both can occur in *any* round, not just the
/// first:
///
/// * A match restart (after a knife round, or ending warmup) drops into a
///   warmup that sits inside the opening round's freeze window, where players
///   shoot each other freely.
/// * A pause — a disconnect and reconnect, a tech pause — ends with the server
///   re-seating every player, which respawns them all and is reported as a
///   `player_death` with weapon `world` for the entire server on one tick.
fn freeze_windows(rounds: &[Round]) -> Vec<(i32, i32)> {
    let mut windows: Vec<(i32, i32)> = rounds
        .iter()
        .filter_map(|r| match (r.start_tick, r.freeze_end_tick) {
            (Some(start), Some(end)) if start < end => Some((start, end)),
            _ => None,
        })
        .collect();
    windows.sort_unstable();
    windows
}

/// Whether `tick` falls inside any freeze period. `windows` must be ascending.
fn in_freeze(tick: i32, windows: &[(i32, i32)]) -> bool {
    // Right-most window whose start is <= tick; only that one can contain it,
    // since freeze periods never overlap.
    let idx = windows.partition_point(|&(start, _)| start <= tick);
    idx > 0 && tick < windows[idx - 1].1
}

/// Index of the round a tick belongs to, or `None` when it is not live play:
/// pre-match / warmup ticks before the first round starts, or any tick inside a
/// freeze period. `starts` and `windows` must be ascending.
fn round_of(tick: i32, starts: &[i32], windows: &[(i32, i32)]) -> Option<usize> {
    if starts.first().is_none_or(|&s| tick < s) || in_freeze(tick, windows) {
        return None;
    }
    match starts.binary_search(&tick) {
        Ok(i) => Some(i),
        Err(i) => Some(i - 1),
    }
}

/// Whether an attacker and victim are on opposing sides, treating an unknown
/// side as "enemy" so world / unresolved cases still count. Used for kills.
fn is_enemy(attacker_side: &Option<String>, victim_side: &Option<String>) -> bool {
    match (attacker_side, victim_side) {
        (Some(a), Some(v)) => a != v,
        _ => true,
    }
}

/// Whether an attacker and victim are *confirmed* to be on opposing sides —
/// both resolved and different. Used for ADR, which must exclude team, self,
/// and world damage, so unresolved cases do **not** count.
fn is_confirmed_enemy(attacker_side: &Option<String>, victim_side: &Option<String>) -> bool {
    matches!((attacker_side, victim_side), (Some(a), Some(v)) if a != v)
}

/// Whether a `player_hurt` / `player_death` weapon string names a damaging
/// grenade (HE or the molotov / incendiary fire), for utility-damage tallying.
fn is_utility_weapon(weapon: &str) -> bool {
    [
        "hegrenade",
        "inferno",
        "molotov",
        "incgrenade",
        "incendiary",
    ]
    .iter()
    .any(|w| weapon.contains(w))
}

/// Compute per-player statistics from the kill / damage / round datasets.
///
/// `trade_ticks` is the trade window in ticks (see [`Parser::player_stats`] for
/// the default derived from the tick rate).
pub fn player_stats(
    kills: &[Kill],
    damages: &[Damage],
    blinds: &[Blind],
    shots: &[Shot],
    rounds: &[Round],
    trade_ticks: i32,
    exclude_knife_rounds: bool,
) -> Vec<PlayerStats> {
    let total_rounds = rounds.len();
    // Knife rounds don't count toward the score, so their kills / deaths /
    // assists / damage — and the rounds themselves in every denominator — are
    // excluded by default.
    let knife_rounds: HashSet<usize> = if exclude_knife_rounds {
        rounds
            .iter()
            .enumerate()
            .filter(|(_, r)| r.is_knife_round)
            .map(|(i, _)| i)
            .collect()
    } else {
        HashSet::new()
    };
    let num_rounds = (total_rounds - knife_rounds.len()) as i32;
    let starts = round_starts(rounds);
    let freezes = freeze_windows(rounds);

    // Kills in tick order, for opening-kill and trade detection.
    let mut ordered: Vec<&Kill> = kills.iter().collect();
    ordered.sort_by_key(|k| k.tick);

    // Mark each kill whose victim's death was traded: the killer is themselves
    // killed by a teammate of the victim within the trade window.
    let n = ordered.len();
    let mut is_traded = vec![false; n];
    for i in 0..n {
        let Some(attacker) = ordered[i].attacker_steamid else {
            continue;
        };
        if ordered[i].victim_side.is_none() {
            continue;
        }
        for kill2 in ordered.iter().skip(i + 1) {
            if kill2.tick - ordered[i].tick > trade_ticks {
                break;
            }
            if kill2.tick > ordered[i].tick
                && kill2.victim_steamid == Some(attacker)
                && kill2.attacker_side == ordered[i].victim_side
            {
                is_traded[i] = true;
                break;
            }
        }
    }

    let mut acc: HashMap<u64, Acc> = HashMap::new();
    let mut round_has_opening: HashSet<usize> = HashSet::new();

    for (i, k) in ordered.iter().enumerate() {
        let Some(round) = round_of(k.tick, &starts, &freezes) else {
            continue;
        };
        if knife_rounds.contains(&round) {
            continue;
        }

        // Attacker: a kill counts if it is against an enemy (not a suicide or
        // team kill).
        if let Some(attacker) = k.attacker_steamid
            && k.victim_steamid != Some(attacker)
            && is_enemy(&k.attacker_side, &k.victim_side)
        {
            let a = acc.entry(attacker).or_default();
            if let Some(name) = &k.attacker_name {
                a.name = name.clone();
            }
            a.kills += 1;
            if k.headshot {
                a.headshot_kills += 1;
            }
            *a.kill_rounds.entry(round).or_default() += 1;
        }

        // Victim.
        if let Some(victim) = k.victim_steamid {
            let a = acc.entry(victim).or_default();
            if a.name.is_empty()
                && let Some(name) = &k.victim_name
            {
                a.name = name.clone();
            }
            a.deaths += 1;
            a.death_rounds.insert(round);
            if is_traded[i] {
                a.traded_deaths += 1;
                a.traded_rounds.insert(round);
            }
        }

        // Assister. An assist only counts against an opponent — a player never
        // gets an assist for damaging a teammate. Flash assists are a subset of
        // assists (counted only when the assist itself is), never a separate
        // total.
        if let Some(assister) = k.assister_steamid {
            let team_assist =
                matches!((&k.assister_side, &k.victim_side), (Some(s), Some(v)) if s == v);
            if !team_assist {
                let a = acc.entry(assister).or_default();
                if a.name.is_empty()
                    && let Some(name) = &k.assister_name
                {
                    a.name = name.clone();
                }
                a.assists += 1;
                if k.assist_flash {
                    a.flash_assists += 1;
                }
                a.assist_rounds.insert(round);
            }
        }

        // Opening kill / death: the first kill seen for this round.
        if round_has_opening.insert(round) {
            if let Some(attacker) = k.attacker_steamid
                && k.victim_steamid != Some(attacker)
            {
                acc.entry(attacker).or_default().opening_kills += 1;
            }
            if let Some(victim) = k.victim_steamid {
                acc.entry(victim).or_default().opening_deaths += 1;
            }
        }
    }

    // Damage for ADR: the *actual* HP removed from enemies during live rounds.
    //
    // A victim's health before a hit is their health after the previous hit
    // that round (100 at the round's first hit). Chaining this way caps a
    // killing blow at the victim's remaining HP rather than the weapon's raw
    // damage — an AWP that "does 115" to a 40 HP enemy removes 40, not 115, so
    // reconstructing `health_pre = min(post + dmg, 100)` per hit over-counts
    // finishing blows on wounded enemies. Every hit on a victim (team, self,
    // world included) advances the chain, but only confirmed enemy damage is
    // credited to the attacker.
    let mut victim_health: HashMap<(usize, u64), i32> = HashMap::new();
    for d in damages {
        let Some(round) = round_of(d.tick, &starts, &freezes) else {
            continue;
        };
        if knife_rounds.contains(&round) {
            continue;
        }
        let removed = match d.victim_steamid {
            Some(victim) => {
                // 100 (full health) at the round's first hit on this victim.
                let before = victim_health.get(&(round, victim)).copied().unwrap_or(100);
                victim_health.insert((round, victim), d.health_post);
                (before - d.health_post).max(0)
            }
            // Unresolved victim — cannot chain; fall back to the per-hit value.
            None => (d.health_pre - d.health_post).max(0),
        };
        let Some(attacker) = d.attacker_steamid else {
            continue;
        };
        if d.victim_steamid == Some(attacker)
            || !is_confirmed_enemy(&d.attacker_side, &d.victim_side)
        {
            continue;
        }
        let a = acc.entry(attacker).or_default();
        a.damage += removed;
        if is_utility_weapon(&d.weapon) {
            a.utility_damage += removed;
        }
    }

    // Flashes thrown (every flashbang the player fired), and how many enemies it
    // blinded / for how long (from resolved flash events on opposing sides).
    for s in shots {
        if !s.weapon.contains("flashbang") {
            continue;
        }
        let Some(round) = round_of(s.tick, &starts, &freezes) else {
            continue;
        };
        if knife_rounds.contains(&round) {
            continue;
        }
        if let Some(thrower) = s.steamid {
            let a = acc.entry(thrower).or_default();
            if a.name.is_empty()
                && let Some(name) = &s.name
            {
                a.name = name.clone();
            }
            a.flashes_thrown += 1;
        }
    }
    for b in blinds {
        let Some(round) = round_of(b.tick, &starts, &freezes) else {
            continue;
        };
        if knife_rounds.contains(&round) {
            continue;
        }
        // Only enemy blinds count — a team-flash or self-flash is not credited.
        if !is_confirmed_enemy(&b.attacker_side, &b.victim_side) {
            continue;
        }
        if let Some(attacker) = b.attacker_steamid {
            let a = acc.entry(attacker).or_default();
            if a.name.is_empty()
                && let Some(name) = &b.attacker_name
            {
                a.name = name.clone();
            }
            a.enemies_flashed += 1;
            a.flash_duration_dealt += b.duration;
        }
    }

    let denom = num_rounds.max(1) as f32;
    let mut out: Vec<PlayerStats> = acc
        .into_iter()
        .map(|(steamid, a)| {
            let (mut m2, mut m3, mut m4, mut m5) = (0, 0, 0, 0);
            for &count in a.kill_rounds.values() {
                match count {
                    2 => m2 += 1,
                    3 => m3 += 1,
                    4 => m4 += 1,
                    c if c >= 5 => m5 += 1,
                    _ => {}
                }
            }

            // KAST: a round counts if the player got a kill or assist, survived,
            // or was traded.
            let kast_rounds = (0..total_rounds)
                .filter(|r| !knife_rounds.contains(r))
                .filter(|r| {
                    a.kill_rounds.contains_key(r)
                        || a.assist_rounds.contains(r)
                        || !a.death_rounds.contains(r)
                        || a.traded_rounds.contains(r)
                })
                .count() as f32;

            let headshot_pct = if a.kills > 0 {
                a.headshot_kills as f32 / a.kills as f32 * 100.0
            } else {
                0.0
            };

            PlayerStats {
                steamid,
                name: a.name,
                rounds_played: num_rounds,
                kills: a.kills,
                deaths: a.deaths,
                assists: a.assists,
                flash_assists: a.flash_assists,
                headshot_kills: a.headshot_kills,
                headshot_pct,
                opening_kills: a.opening_kills,
                opening_deaths: a.opening_deaths,
                traded_deaths: a.traded_deaths,
                multikill_2k: m2,
                multikill_3k: m3,
                multikill_4k: m4,
                multikill_5k: m5,
                kast: kast_rounds / denom * 100.0,
                adr: a.damage as f32 / denom,
                utility_damage: a.utility_damage,
                flashes_thrown: a.flashes_thrown,
                enemies_flashed: a.enemies_flashed,
                flash_duration_dealt: a.flash_duration_dealt,
            }
        })
        .collect();

    // Most kills first, then Steam id for a stable order.
    out.sort_by(|a, b| b.kills.cmp(&a.kills).then(a.steamid.cmp(&b.steamid)));
    out
}

impl Parser {
    /// Per-player match statistics (see the [module docs](self)).
    ///
    /// Parses the kill, damage, and round datasets and aggregates them with a
    /// trade window of `TRADE_SECONDS` converted to ticks using the demo's
    /// tick rate.
    pub fn player_stats(&self, exclude_knife_rounds: bool) -> Result<Vec<PlayerStats>> {
        // One combined pass yields both kills and damages (see event_datasets).
        let events = self.event_datasets()?;
        let rounds = self.rounds()?;
        Ok(self.player_stats_from(&events, &rounds, exclude_knife_rounds))
    }

    /// Aggregate per-player statistics from an **already-decoded**
    /// [`EventDatasets`] and round list, skipping the two entity passes
    /// [`player_stats`](Self::player_stats) would otherwise run. Used by callers
    /// that already hold both (e.g. a batched parallel parse).
    pub fn player_stats_from(
        &self,
        events: &EventDatasets,
        rounds: &[Round],
        exclude_knife_rounds: bool,
    ) -> Vec<PlayerStats> {
        let trade_ticks = (TRADE_SECONDS * self.tickrate()).round() as i32;
        player_stats(
            &events.kills,
            &events.damages,
            &events.blinds,
            &events.shots,
            rounds,
            trade_ticks,
            exclude_knife_rounds,
        )
    }

    /// Ticks per second, from the demo's playback timing (falling back to
    /// `DEFAULT_TICKRATE` when it is unavailable).
    pub fn tickrate(&self) -> f32 {
        self.file_info()
            .ok()
            .and_then(|i| match (i.playback_ticks, i.playback_time) {
                (Some(ticks), Some(time)) if time > 0.0 => Some(ticks as f32 / time),
                _ => None,
            })
            .filter(|r| r.is_finite() && *r > 0.0)
            .unwrap_or(DEFAULT_TICKRATE)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn round(num: i32, start: i32, end: i32) -> Round {
        Round {
            round_num: num,
            start_tick: Some(start),
            freeze_end_tick: Some(start),
            end_tick: end,
            official_end_tick: Some(end),
            winner: 2,
            winner_side: "terrorist".into(),
            reason: 0,
            reason_name: "t_win".into(),
            is_knife_round: false,
        }
    }

    fn kill(tick: i32, attacker: u64, aside: &str, victim: u64, vside: &str) -> Kill {
        Kill {
            tick,
            attacker_steamid: Some(attacker),
            attacker_name: Some(format!("p{attacker}")),
            attacker_side: Some(aside.into()),
            victim_steamid: Some(victim),
            victim_name: Some(format!("p{victim}")),
            victim_side: Some(vside.into()),
            ..Default::default()
        }
    }

    fn find(stats: &[PlayerStats], steamid: u64) -> &PlayerStats {
        stats.iter().find(|s| s.steamid == steamid).unwrap()
    }

    #[test]
    fn opening_and_multikills() {
        let rounds = vec![round(1, 0, 1000), round(2, 2000, 3000)];
        // Round 1: player 1 (T) triple-kills CTs; player 4 opens on player 1.
        let kills = vec![
            kill(100, 4, "counter-terrorist", 1, "terrorist"), // opening: 4 kills 1
            kill(200, 1, "terrorist", 5, "counter-terrorist"),
            kill(250, 1, "terrorist", 6, "counter-terrorist"),
            kill(300, 1, "terrorist", 7, "counter-terrorist"),
        ];
        let stats = player_stats(&kills, &[], &[], &[], &rounds, 320, false);

        let p1 = find(&stats, 1);
        assert_eq!(p1.kills, 3);
        assert_eq!(p1.multikill_3k, 1);
        assert_eq!(p1.multikill_2k, 0);
        assert_eq!(p1.deaths, 1);
        assert_eq!(p1.opening_deaths, 1);

        let p4 = find(&stats, 4);
        assert_eq!(p4.opening_kills, 1);
        assert_eq!(p4.kills, 1);
    }

    #[test]
    fn traded_death_within_window() {
        let rounds = vec![round(1, 0, 1000)];
        // Player 2 (CT) kills player 1 (T); teammate 3 (T) trades within window.
        let kills = vec![
            kill(100, 2, "counter-terrorist", 1, "terrorist"),
            kill(300, 3, "terrorist", 2, "counter-terrorist"),
        ];
        let stats = player_stats(&kills, &[], &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats, 1).traded_deaths, 1);
        // Outside the window: no trade.
        let kills_late = vec![
            kill(100, 2, "counter-terrorist", 1, "terrorist"),
            kill(500, 3, "terrorist", 2, "counter-terrorist"),
        ];
        let stats_late = player_stats(&kills_late, &[], &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats_late, 1).traded_deaths, 0);
    }

    #[test]
    fn kast_counts_kill_survival_and_trade() {
        let rounds = vec![round(1, 0, 1000), round(2, 2000, 3000)];
        // Player 1 kills in round 1 (KAST), survives round 2 (KAST) => 100%.
        let kills = vec![kill(100, 1, "terrorist", 5, "counter-terrorist")];
        let stats = player_stats(&kills, &[], &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats, 1).kast, 100.0);
        // Player 5 died round 1 untraded, absent round 2 (survived) => 50%.
        assert_eq!(find(&stats, 5).kast, 50.0);
    }

    #[test]
    fn adr_uses_capped_damage_over_rounds() {
        let rounds = vec![round(1, 0, 1000), round(2, 2000, 3000)];
        let damages = vec![Damage {
            tick: 100,
            attacker_steamid: Some(1),
            attacker_side: Some("terrorist".into()),
            victim_steamid: Some(5),
            victim_side: Some("counter-terrorist".into()),
            health_pre: 100,
            health_post: 0,
            dmg_health: 444, // raw overkill ignored; capped HP removed is 100
            ..Default::default()
        }];
        let stats = player_stats(&[], &damages, &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats, 1).adr, 50.0); // 100 damage / 2 rounds
    }

    #[test]
    fn adr_excludes_team_self_and_world_damage() {
        let rounds = vec![round(1, 0, 1000)];
        let dmg = |tick,
                   attacker: Option<u64>,
                   aside: Option<&str>,
                   victim: u64,
                   vside: &str,
                   pre,
                   post| Damage {
            tick,
            attacker_steamid: attacker,
            attacker_side: aside.map(Into::into),
            victim_steamid: Some(victim),
            victim_side: Some(vside.into()),
            health_pre: pre,
            health_post: post,
            ..Default::default()
        };
        let damages = vec![
            dmg(
                100,
                Some(1),
                Some("terrorist"),
                5,
                "counter-terrorist",
                100,
                50,
            ), // enemy: +50
            dmg(110, Some(1), Some("terrorist"), 2, "terrorist", 100, 70), // team: excluded
            dmg(120, Some(1), Some("terrorist"), 1, "terrorist", 100, 80), // self: excluded
            dmg(130, None, None, 5, "counter-terrorist", 100, 60),         // world: excluded
        ];
        let stats = player_stats(&[], &damages, &[], &[], &rounds, 320, false);
        // Only the 50 enemy damage counts, over 1 round.
        assert_eq!(find(&stats, 1).adr, 50.0);
    }

    /// A round whose freeze period is distinct from its start, for the
    /// pre-match-boundary tests below.
    fn round_with_freeze(num: i32, start: i32, freeze_end: i32, end: i32) -> Round {
        Round {
            freeze_end_tick: Some(freeze_end),
            ..round(num, start, end)
        }
    }

    #[test]
    fn freeze_ticks_are_not_live_play() {
        let rounds = vec![
            round_with_freeze(1, 100, 500, 900),
            round_with_freeze(2, 1000, 1100, 1900),
        ];
        let starts = round_starts(&rounds);
        let freezes = freeze_windows(&rounds);
        assert_eq!(freezes, vec![(100, 500), (1000, 1100)]);

        // Pre-match, before any round.
        assert_eq!(round_of(50, &starts, &freezes), None);
        // Inside a freeze period — the first round's *and* a later one's.
        assert_eq!(round_of(200, &starts, &freezes), None);
        assert_eq!(round_of(1050, &starts, &freezes), None);
        // Live play, and the post-round window between rounds.
        assert_eq!(round_of(500, &starts, &freezes), Some(0));
        assert_eq!(round_of(600, &starts, &freezes), Some(0));
        assert_eq!(round_of(950, &starts, &freezes), Some(0));
        assert_eq!(round_of(1500, &starts, &freezes), Some(1));
    }

    #[test]
    fn freeze_period_kills_are_ignored_in_every_round() {
        // A pause ending in a server re-seat respawns everyone mid-match, which
        // the demo reports as deaths during the round's freeze period.
        let rounds = vec![
            round_with_freeze(1, 100, 500, 900),
            round_with_freeze(2, 1000, 1100, 1900),
        ];
        let kills = vec![
            kill(200, 1, "terrorist", 5, "counter-terrorist"), // round 1 freeze: ignored
            kill(600, 1, "terrorist", 6, "counter-terrorist"), // live: counts
            kill(1050, 1, "terrorist", 7, "counter-terrorist"), // round 2 freeze: ignored
            kill(1500, 1, "terrorist", 8, "counter-terrorist"), // live: counts
        ];
        let stats = player_stats(&kills, &[], &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats, 1).kills, 2);
        // Freeze-period victims must not be charged with a death either.
        assert!(stats.iter().all(|s| s.steamid != 5 && s.steamid != 7));
        assert_eq!(find(&stats, 6).deaths, 1);
        assert_eq!(find(&stats, 8).deaths, 1);
    }

    #[test]
    fn rounds_without_a_known_freeze_have_no_window() {
        // Missing or degenerate freeze bounds must not fabricate a window that
        // would silently swallow real kills.
        let rounds = vec![
            Round {
                freeze_end_tick: None,
                ..round(1, 100, 900)
            },
            round_with_freeze(2, 1000, 1000, 1900), // zero-length
        ];
        let freezes = freeze_windows(&rounds);
        assert!(freezes.is_empty());

        let starts = round_starts(&rounds);
        assert_eq!(round_of(200, &starts, &freezes), Some(0));
        assert_eq!(round_of(1000, &starts, &freezes), Some(1));
    }
}
