//! Aggregate player statistics computed from the kill, damage, and round
//! datasets.
//!
//! [`player_stats`] is a pure function over the datasets, so it is easy to test
//! and reuse; [`Parser::player_stats`] is the convenience entry point that
//! parses the demo and calls it with a trade window derived from the tick rate.
//!
//! Definitions:
//! - **Opening kill / death** — the attacker / victim of the *first* kill of a
//!   round.
//! - **Traded death** — the earliest qualifying teammate death avenged by a kill
//!   within the trade window (default 5.25 seconds). Each kill trades one death.
//! - **Clutch** — a round in which the player was the last alive on their side
//!   against one or more living opponents. The situation is fixed at the moment
//!   they become last alive (so a 1v3 that becomes a 1v1 is still a 1v3), and is
//!   *won* if their side wins the round.
//! - **KAST** — percentage of rounds in which the player got a **K**ill,
//!   **A**ssist, **S**urvived, or was **T**raded.
//! - **ADR** — recorded enemy damage per round. Each hit's integer damage is
//!   capped at the victim's previous reported health (100 for the first hit).
//!   All hits update that health, including team, self, and world damage,
//!   which do not receive credit. Health rounding does not add damage.
//! - **Multi-kill rounds** — rounds with exactly 2 / 3 / 4 / 5+ kills.
//!
//! Player rosters are taken from everyone who appears in a kill or damage, and
//! every player is assumed to have played every round — the denominator for
//! KAST and ADR is the match's total round count. Players who join or leave
//! mid-match are therefore approximate.

use std::collections::{HashMap, HashSet};

use crate::datasets::{
    Blind, Damage, EventDatasets, Kill, Round, Shot, TRADE_SECONDS, trade_flags,
};
use crate::demo::Parser;
use crate::error::Result;

/// Fallback tick rate when the demo does not report playback timing.
const DEFAULT_TICKRATE: f32 = 64.0;
/// Largest clutch broken out into its own counter (`clutch_1v1` … `clutch_1v5`).
const MAX_CLUTCH: usize = 5;

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
    // ── Clutches ──
    /// Rounds entered as the last player alive against at least one opponent.
    pub clutches_played: i32,
    /// How many of those rounds their side went on to win.
    pub clutches_won: i32,
    /// Clutches *won* against exactly 1 / 2 / 3 / 4 / 5-or-more opponents.
    pub clutch_1v1: i32,
    pub clutch_1v2: i32,
    pub clutch_1v3: i32,
    pub clutch_1v4: i32,
    pub clutch_1v5: i32,
    // ── Utility ──
    /// Recorded grenade damage dealt to enemies (HE + molotov / incendiary),
    /// capped at remaining health like ADR.
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
    clutches_played: i32,
    clutches_won: i32,
    /// Opponents faced (1-based, capped at [`MAX_CLUTCH`]) → clutches won.
    clutch_wins: HashMap<usize, i32>,
}

/// Exact totals across recordings of separate, complete rounds.
///
/// Each part is evaluated separately: tick counters and entity identities may
/// restart, and trades or flash effects must not cross recording boundaries.
/// Callers must reject overlapping or missing rounds before adding parts.
#[derive(Default)]
pub struct PlayerStatsAccumulator {
    total_rounds: usize,
    knife_rounds: HashSet<usize>,
    acc: HashMap<u64, Acc>,
}

impl PlayerStatsAccumulator {
    /// Add one independently decoded recording without rounding its totals.
    ///
    /// Event datasets must be in recorded tick order. Events after the last
    /// completed round's official end are excluded, including a following freeze.
    pub fn add_part(
        &mut self,
        events: &EventDatasets,
        rounds: &[Round],
        tickrate: f32,
        exclude_knife_rounds: bool,
    ) {
        let Some(last) = rounds.last() else {
            return;
        };
        let end = last.official_end_tick.unwrap_or(last.end_tick);
        let tickrate = if tickrate.is_finite() && tickrate > 0.0 {
            tickrate
        } else {
            DEFAULT_TICKRATE
        };
        let other = collect_stats(
            completed_rows(&events.kills, end, |row| row.tick),
            completed_rows(&events.damages, end, |row| row.tick),
            completed_rows(&events.blinds, end, |row| row.tick),
            completed_rows(&events.shots, end, |row| row.tick),
            rounds,
            (TRADE_SECONDS * tickrate).round() as i32,
            exclude_knife_rounds,
            tickrate,
        );
        let offset = self.total_rounds;
        self.knife_rounds
            .extend(other.knife_rounds.into_iter().map(|round| round + offset));
        self.total_rounds += other.total_rounds;
        for (steamid, incoming) in other.acc {
            let total = self.acc.entry(steamid).or_default();
            if !incoming.name.is_empty() {
                total.name = incoming.name;
            }
            macro_rules! sum {
                ($($field:ident),+ $(,)?) => { $(total.$field += incoming.$field;)+ };
            }
            sum!(
                kills,
                deaths,
                assists,
                flash_assists,
                headshot_kills,
                opening_kills,
                opening_deaths,
                traded_deaths,
                damage,
                utility_damage,
                flashes_thrown,
                enemies_flashed,
                flash_duration_dealt,
                clutches_played,
                clutches_won
            );
            total.kill_rounds.extend(
                incoming
                    .kill_rounds
                    .into_iter()
                    .map(|(round, count)| (round + offset, count)),
            );
            total.assist_rounds.extend(
                incoming
                    .assist_rounds
                    .into_iter()
                    .map(|round| round + offset),
            );
            total.death_rounds.extend(
                incoming
                    .death_rounds
                    .into_iter()
                    .map(|round| round + offset),
            );
            total.traded_rounds.extend(
                incoming
                    .traded_rounds
                    .into_iter()
                    .map(|round| round + offset),
            );
            for (opponents, wins) in incoming.clutch_wins {
                *total.clutch_wins.entry(opponents).or_default() += wins;
            }
        }
    }
}

/// Borrow the complete-round prefix without copying event payloads.
fn completed_rows<T>(rows: &[T], end_tick: i32, tick: impl Fn(&T) -> i32) -> &[T] {
    &rows[..rows.partition_point(|row| tick(row) <= end_tick)]
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

/// The two playing sides, in the order [`team_name`](crate::team_name) reports
/// them. Rosters and clutches only ever concern these.
const SIDES: [&str; 2] = ["terrorist", "counter-terrorist"];

/// One player's observed side, per round they were seen in.
type SideObservations = HashMap<u64, HashMap<usize, String>>;

/// Record the side of each player in each round.
///
/// [`player_stats`] does not read entity state. It uses the event datasets to
/// reconstruct team membership. Each dataset that has a player and a side
/// contributes to the result.
fn side_observations(
    kills: &[Kill],
    damages: &[Damage],
    blinds: &[Blind],
    shots: &[Shot],
    starts: &[i32],
    windows: &[(i32, i32)],
) -> SideObservations {
    let mut obs: SideObservations = HashMap::new();
    let mut note = |tick: i32, steamid: Option<u64>, side: Option<&str>| {
        if let Some(steamid) = steamid
            && let Some(side) = side
            && SIDES.contains(&side)
            && let Some(round) = round_of(tick, starts, windows)
        {
            obs.entry(steamid)
                .or_default()
                .insert(round, side.to_owned());
        }
    };
    for kill in kills {
        note(
            kill.tick,
            kill.attacker_steamid,
            kill.attacker_side.as_deref(),
        );
        note(kill.tick, kill.victim_steamid, kill.victim_side.as_deref());
        note(
            kill.tick,
            kill.assister_steamid,
            kill.assister_side.as_deref(),
        );
    }
    for damage in damages {
        note(
            damage.tick,
            damage.attacker_steamid,
            damage.attacker_side.as_deref(),
        );
        note(
            damage.tick,
            damage.victim_steamid,
            damage.victim_side.as_deref(),
        );
    }
    for blind in blinds {
        note(
            blind.tick,
            blind.attacker_steamid,
            blind.attacker_side.as_deref(),
        );
        note(
            blind.tick,
            blind.victim_steamid,
            blind.victim_side.as_deref(),
        );
    }
    for shot in shots {
        note(shot.tick, shot.steamid, shot.side.as_deref());
    }
    obs
}

/// Which *half* each round belongs to, as a 0-based index.
///
/// Sides swap at halftime and again each overtime half, and a player's side is
/// constant within a half — which is what lets a quiet round be filled in from
/// the rounds around it. The boundaries are found from the observations
/// themselves (a round where most players who also played the previous round
/// changed side) rather than from a match-format assumption, so MR12, MR15, and
/// overtime all work.
fn halves(obs: &SideObservations, total_rounds: usize) -> Vec<usize> {
    // Round -> the sides observed that round, by player.
    let mut by_round: Vec<HashMap<u64, &str>> = vec![HashMap::new(); total_rounds];
    for (&steamid, rounds) in obs {
        for (&round, side) in rounds {
            if let Some(slot) = by_round.get_mut(round) {
                slot.insert(steamid, side.as_str());
            }
        }
    }

    let mut half = vec![0usize; total_rounds];
    for round in 1..total_rounds {
        let (prev, cur) = (&by_round[round - 1], &by_round[round]);
        let shared: Vec<(&str, &str)> = cur
            .iter()
            .filter_map(|(id, side)| prev.get(id).map(|before| (*before, *side)))
            .collect();
        let flipped = shared.iter().filter(|(before, now)| before != now).count();
        // A swap moves everyone at once, so a simple majority is decisive; with
        // nobody in common there is no evidence of a swap.
        let swapped = !shared.is_empty() && flipped * 2 > shared.len();
        half[round] = half[round - 1] + usize::from(swapped);
    }
    half
}

/// Per-round side rosters: for each round, the Steam ids on each side.
///
/// A player is on a side's roster for every round between their first and last
/// appearance in the match, using the side they held during that round's half —
/// so a player who happens to do nothing all round is still counted as alive.
/// Without that, a silent teammate would look dead and every survivor would look
/// like a clutch.
fn round_rosters(
    obs: &SideObservations,
    total_rounds: usize,
) -> Vec<HashMap<&'static str, HashSet<u64>>> {
    let half = halves(obs, total_rounds);
    let mut rosters: Vec<HashMap<&'static str, HashSet<u64>>> = vec![HashMap::new(); total_rounds];

    for (&steamid, rounds) in obs {
        if rounds.is_empty() {
            continue;
        }
        // Only the rounds this player was actually present for — outside that
        // span they had not joined yet, or had already left.
        let first = *rounds.keys().min().expect("non-empty");
        let last = *rounds.keys().max().expect("non-empty");

        // Their side in each half, from the observations falling in that half.
        // Constant within a half, so the first one seen settles it.
        let mut side_in_half: HashMap<usize, &'static str> = HashMap::new();
        for (&round, side) in rounds {
            let Some(&h) = half.get(round) else { continue };
            let Some(canonical) = SIDES.iter().find(|s| **s == side.as_str()) else {
                continue;
            };
            side_in_half.entry(h).or_insert(canonical);
        }

        for (round, roster) in rosters.iter_mut().enumerate().take(last + 1).skip(first) {
            if let Some(&h) = half.get(round)
                && let Some(&side) = side_in_half.get(&h)
            {
                roster.entry(side).or_default().insert(steamid);
            }
        }
    }
    rosters
}

/// A 1-vs-many situation a player was left in: who they were, how many opponents
/// were still alive at that moment, and whether their side won the round.
struct Clutch {
    steamid: u64,
    opponents: usize,
    won: bool,
}

/// Find every clutch: a player left as the last alive on their side with at
/// least one opponent still up.
///
/// The situation is fixed at the moment the player becomes last alive, so a 1v3
/// stays a 1v3 even after they trade two of the three. Only the first such moment
/// per side per round counts. A side that starts a round with a single player
/// (say, after a disconnect) never *becomes* last alive and so is not a clutch.
fn clutches(
    kills: &[Kill],
    order: &[usize],
    rounds: &[Round],
    starts: &[i32],
    windows: &[(i32, i32)],
    knife_rounds: &HashSet<usize>,
    rosters: &[HashMap<&'static str, HashSet<u64>>],
) -> Vec<Clutch> {
    let mut out = Vec::new();
    // Kill indices bucketed by round, still in tick order.
    let mut by_round: HashMap<usize, Vec<usize>> = HashMap::new();
    for &i in order {
        if let Some(round) = round_of(kills[i].tick, starts, windows) {
            by_round.entry(round).or_default().push(i);
        }
    }

    for (round, indices) in by_round {
        if knife_rounds.contains(&round) {
            continue;
        }
        let Some(roster) = rosters.get(round) else {
            continue;
        };
        let Some(winner) = rounds.get(round).map(|r| r.winner_side.as_str()) else {
            continue;
        };
        let mut alive: HashMap<&str, HashSet<u64>> = SIDES
            .iter()
            .map(|&s| (s, roster.get(s).cloned().unwrap_or_default()))
            .collect();
        let mut recorded: HashSet<&str> = HashSet::new();

        for &i in &indices {
            let Some(victim) = kills[i].victim_steamid else {
                continue;
            };
            // Prefer the event's own side, but fall back to whichever roster
            // holds the victim — an unresolved side must not leave them "alive".
            let side = kills[i]
                .victim_side
                .as_deref()
                .filter(|s| SIDES.contains(s))
                .or_else(|| {
                    SIDES
                        .iter()
                        .copied()
                        .find(|s| alive.get(s).is_some_and(|set| set.contains(&victim)))
                });
            let Some(side) = side else { continue };
            if !alive.get_mut(side).is_some_and(|set| set.remove(&victim)) {
                continue; // not on this side's roster, or already dead
            }
            if recorded.contains(side) {
                continue;
            }

            // Only the side that just lost someone can newly be down to its last
            // player — the opponents' count did not change. And because the
            // removal above decremented by exactly one, a size of 1 here *is* the
            // 2 -> 1 transition, so a side that fielded one player all round (a
            // disconnect, say) never registers.
            let survivors = &alive[side];
            let opponent = SIDES
                .iter()
                .copied()
                .find(|s| *s != side)
                .expect("two sides");
            let opponents = alive[opponent].len();
            if survivors.len() == 1 && opponents > 0 {
                recorded.insert(side);
                out.push(Clutch {
                    steamid: *survivors.iter().next().expect("exactly one"),
                    opponents,
                    won: side == winner,
                });
            }
        }
    }
    out
}

/// Return whether the attacker and victim are on opposing sides.
///
/// Treat an unknown side as an enemy. This rule includes world and unresolved
/// kills.
fn is_enemy(attacker_side: Option<&str>, victim_side: Option<&str>) -> bool {
    match (attacker_side, victim_side) {
        (Some(a), Some(v)) => a != v,
        _ => true,
    }
}

/// Return whether the attacker and victim have known, opposing sides.
///
/// Use this rule for ADR. It excludes team damage, self damage, world damage,
/// and unresolved damage.
fn is_confirmed_enemy(attacker_side: Option<&str>, victim_side: Option<&str>) -> bool {
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
/// the default derived from the tick rate). Flash timing uses the CS2 default
/// of 64 ticks per second; use [`player_stats_at_tickrate`] for another rate.
pub fn player_stats(
    kills: &[Kill],
    damages: &[Damage],
    blinds: &[Blind],
    shots: &[Shot],
    rounds: &[Round],
    trade_ticks: i32,
    exclude_knife_rounds: bool,
) -> Vec<PlayerStats> {
    player_stats_at_tickrate(
        kills,
        damages,
        blinds,
        shots,
        rounds,
        trade_ticks,
        exclude_knife_rounds,
        DEFAULT_TICKRATE,
    )
}

/// Compute stats with an explicit tick rate for flash-assist timing.
///
/// Recorded assisters and qualifying flash throwers each receive one assist per
/// kill. Flash assists require an active enemy blind in the same round; the
/// victim's full pawn identity is checked when available. Invalid tick rates
/// use the CS2 default of 64 ticks per second.
#[allow(clippy::too_many_arguments)]
pub fn player_stats_at_tickrate(
    kills: &[Kill],
    damages: &[Damage],
    blinds: &[Blind],
    shots: &[Shot],
    rounds: &[Round],
    trade_ticks: i32,
    exclude_knife_rounds: bool,
    tickrate: f32,
) -> Vec<PlayerStats> {
    collect_stats(
        kills,
        damages,
        blinds,
        shots,
        rounds,
        trade_ticks,
        exclude_knife_rounds,
        tickrate,
    )
    .finish()
}

#[allow(clippy::too_many_arguments)]
fn collect_stats(
    kills: &[Kill],
    damages: &[Damage],
    blinds: &[Blind],
    shots: &[Shot],
    rounds: &[Round],
    trade_ticks: i32,
    exclude_knife_rounds: bool,
    tickrate: f32,
) -> PlayerStatsAccumulator {
    let tickrate = if tickrate.is_finite() && tickrate > 0.0 {
        f64::from(tickrate)
    } else {
        f64::from(DEFAULT_TICKRATE)
    };
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
    let starts = round_starts(rounds);
    let freezes = freeze_windows(rounds);

    // Kill indices in tick order, for opening-kill detection and the clutch walk.
    let mut order: Vec<usize> = (0..kills.len()).collect();
    order.sort_by_key(|&i| kills[i].tick);

    // Traded deaths come from the same classifier that fills
    // `Kill::victim_traded`, so `traded_deaths` and the kills dataset can never
    // disagree about what a trade is.
    let trades = trade_flags(kills, trade_ticks);

    let mut acc: HashMap<u64, Acc> = HashMap::new();
    let mut round_has_opening: HashSet<usize> = HashSet::new();
    let mut blinds_by_victim: HashMap<u64, Vec<(usize, &Blind)>> = HashMap::new();
    for blind in blinds {
        if let Some(victim) = blind.victim_steamid
            && let Some(round) = round_of(blind.tick, &starts, &freezes)
            && blind.duration.is_finite()
            && blind.duration > 0.0
        {
            blinds_by_victim
                .entry(victim)
                .or_default()
                .push((round, blind));
        }
    }
    let mut assisters: HashMap<u64, (Option<&String>, bool)> = HashMap::new();

    for &i in &order {
        let k = &kills[i];
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
            && is_enemy(k.attacker_side.as_deref(), k.victim_side.as_deref())
        {
            let a = acc.entry(attacker).or_default();
            if let Some(name) = &k.attacker_name {
                a.name.clone_from(name);
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
                a.name.clone_from(name);
            }
            a.deaths += 1;
            a.death_rounds.insert(round);
            if trades[i].1 {
                a.traded_deaths += 1;
                a.traded_rounds.insert(round);
            }
        }

        // Keep the game's assister, then add active flash throwers. The event
        // can name a different player from the one observed blinding the victim.
        assisters.clear();
        if let Some(assister) = k.assister_steamid
            && Some(assister) != k.attacker_steamid
            && Some(assister) != k.victim_steamid
            && !matches!((&k.assister_side, &k.victim_side), (Some(s), Some(v)) if s == v)
        {
            assisters.insert(assister, (k.assister_name.as_ref(), k.assist_flash));
        }
        if let Some(victim) = k.victim_steamid
            && k.attacker_steamid
                .is_some_and(|attacker| attacker != victim)
            && is_confirmed_enemy(k.attacker_side.as_deref(), k.victim_side.as_deref())
        {
            for &(blind_round, blind) in blinds_by_victim.get(&victim).into_iter().flatten() {
                let Some(thrower) = blind.attacker_steamid else {
                    continue;
                };
                let elapsed = (f64::from(k.tick) - f64::from(blind.tick)) / tickrate;
                let different_pawn = k
                    .victim_entity_id
                    .zip(k.victim_entity_serial)
                    .zip(blind.victim_entity_id.zip(blind.victim_entity_serial))
                    .is_some_and(|(kill_pawn, blind_pawn)| kill_pawn != blind_pawn);
                if blind_round != round
                    || elapsed < 0.0
                    || elapsed >= f64::from(blind.duration)
                    || different_pawn
                    || Some(thrower) == k.attacker_steamid
                    || thrower == victim
                    || blind.attacker_side != k.attacker_side
                {
                    continue;
                }
                assisters
                    .entry(thrower)
                    .and_modify(|(name, flash)| {
                        *flash = true;
                        if name.is_none() {
                            *name = blind.attacker_name.as_ref();
                        }
                    })
                    .or_insert((blind.attacker_name.as_ref(), true));
            }
        }
        for (&assister, &(name, flash)) in &assisters {
            let a = acc.entry(assister).or_default();
            if a.name.is_empty()
                && let Some(name) = name
            {
                a.name.clone_from(name);
            }
            a.assists += 1;
            a.flash_assists += i32::from(flash);
            a.assist_rounds.insert(round);
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

    // Use the event's integer damage, capped at remaining health. Reported
    // health can fall by an extra point due to rounding; do not credit it as
    // damage. All hits advance the health chain, including excluded damage,
    // so successive hits in the same tick cannot reuse the victim's health.
    let mut victim_health: HashMap<(usize, u64), i32> = HashMap::new();
    for d in damages {
        let Some(round) = round_of(d.tick, &starts, &freezes) else {
            continue;
        };
        if knife_rounds.contains(&round) {
            continue;
        }
        let before = match d.victim_steamid {
            Some(victim) => victim_health
                .insert((round, victim), d.health_post)
                .unwrap_or(100),
            // Unresolved victim: only the per-event estimate is available.
            None => d.health_pre,
        };
        let removed = d.dmg_health.max(0).min(before.max(0));
        let Some(attacker) = d.attacker_steamid else {
            continue;
        };
        if d.victim_steamid == Some(attacker)
            || !is_confirmed_enemy(d.attacker_side.as_deref(), d.victim_side.as_deref())
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
                a.name.clone_from(name);
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
        if !is_confirmed_enemy(b.attacker_side.as_deref(), b.victim_side.as_deref()) {
            continue;
        }
        if let Some(attacker) = b.attacker_steamid {
            let a = acc.entry(attacker).or_default();
            if a.name.is_empty()
                && let Some(name) = &b.attacker_name
            {
                a.name.clone_from(name);
            }
            a.enemies_flashed += 1;
            a.flash_duration_dealt += b.duration;
        }
    }

    // Clutches, from the per-round side rosters the events imply.
    let rosters = round_rosters(
        &side_observations(kills, damages, blinds, shots, &starts, &freezes),
        total_rounds,
    );
    for clutch in clutches(
        kills,
        &order,
        rounds,
        &starts,
        &freezes,
        &knife_rounds,
        &rosters,
    ) {
        let a = acc.entry(clutch.steamid).or_default();
        a.clutches_played += 1;
        if clutch.won {
            a.clutches_won += 1;
            *a.clutch_wins
                .entry(clutch.opponents.min(MAX_CLUTCH))
                .or_default() += 1;
        }
    }

    PlayerStatsAccumulator {
        total_rounds,
        knife_rounds,
        acc,
    }
}

impl PlayerStatsAccumulator {
    /// Convert exact accumulated counts to the public statistics.
    #[must_use]
    pub fn finish(self) -> Vec<PlayerStats> {
        let Self {
            total_rounds,
            knife_rounds,
            acc,
        } = self;
        let num_rounds = i32::try_from(total_rounds - knife_rounds.len()).unwrap_or(i32::MAX);
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
                    clutches_played: a.clutches_played,
                    clutches_won: a.clutches_won,
                    clutch_1v1: a.clutch_wins.get(&1).copied().unwrap_or(0),
                    clutch_1v2: a.clutch_wins.get(&2).copied().unwrap_or(0),
                    clutch_1v3: a.clutch_wins.get(&3).copied().unwrap_or(0),
                    clutch_1v4: a.clutch_wins.get(&4).copied().unwrap_or(0),
                    clutch_1v5: a.clutch_wins.get(&5).copied().unwrap_or(0),
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
}

impl Parser {
    /// Per-player match statistics (see the [module docs](self)).
    ///
    /// Parses the kill, damage, and round datasets and aggregates them with a
    /// trade window of `TRADE_SECONDS` converted to ticks using the demo's
    /// tick rate.
    pub fn player_stats(&self, exclude_knife_rounds: bool) -> Result<Vec<PlayerStats>> {
        let inputs = self.player_stats_inputs(None)?;
        Ok(self.player_stats_from(
            inputs.event_datasets(),
            inputs.rounds(),
            exclude_knife_rounds,
        ))
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
        self.player_stats_from_parts(
            &events.kills,
            &events.damages,
            &events.blinds,
            &events.shots,
            rounds,
            exclude_knife_rounds,
        )
    }

    /// Aggregate stats from separately cached event dataset slices.
    #[allow(clippy::too_many_arguments)]
    pub fn player_stats_from_parts(
        &self,
        kills: &[Kill],
        damages: &[Damage],
        blinds: &[Blind],
        shots: &[Shot],
        rounds: &[Round],
        exclude_knife_rounds: bool,
    ) -> Vec<PlayerStats> {
        let trade_ticks = (TRADE_SECONDS * self.tickrate()).round() as i32;
        player_stats_at_tickrate(
            kills,
            damages,
            blinds,
            shots,
            rounds,
            trade_ticks,
            exclude_knife_rounds,
            self.tickrate(),
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

    fn blind(
        tick: i32,
        duration: f32,
        thrower: u64,
        side: &str,
        victim: u64,
        vside: &str,
    ) -> Blind {
        Blind {
            tick,
            duration,
            attacker_steamid: Some(thrower),
            attacker_name: Some(format!("p{thrower}")),
            attacker_side: Some(side.into()),
            victim_steamid: Some(victim),
            victim_side: Some(vside.into()),
            ..Default::default()
        }
    }

    fn assist_kills(recorded_flash: bool) -> [Kill; 2] {
        [
            Kill {
                assister_steamid: Some(3),
                assister_name: Some("p3".into()),
                assister_side: Some(T.into()),
                assist_flash: recorded_flash,
                ..kill(100, 1, T, 2, CT)
            },
            kill(150, 5, CT, 4, T),
        ]
    }

    #[test]
    fn multipart_kills_with_equal_local_ticks_are_separate_rounds() {
        let mut total = PlayerStatsAccumulator::default();
        for number in [1, 2] {
            let events = EventDatasets {
                kills: vec![kill(100, 1, T, 2, CT)],
                ..Default::default()
            };
            total.add_part(&events, &[round(number, 0, 1000)], 64.0, true);
        }
        let stats = total.finish();
        let player = find(&stats, 1);
        assert_eq!((player.kills, player.multikill_2k), (2, 0));
    }

    #[test]
    fn multipart_adr_uses_exact_damage_and_all_rounds() {
        let mut total = PlayerStatsAccumulator::default();
        for (health_post, rounds) in [
            (
                0,
                vec![
                    round(1, 0, 1000),
                    round(2, 2000, 3000),
                    round(3, 4000, 5000),
                ],
            ),
            (99, vec![round(4, 0, 1000)]),
        ] {
            let events = EventDatasets {
                damages: vec![Damage {
                    tick: 100,
                    attacker_steamid: Some(1),
                    attacker_side: Some(T.into()),
                    victim_steamid: Some(2),
                    victim_side: Some(CT.into()),
                    health_pre: 100,
                    health_post,
                    dmg_health: 100 - health_post,
                    ..Default::default()
                }],
                ..Default::default()
            };
            total.add_part(&events, &rounds, 64.0, true);
        }
        assert_eq!(find(&total.finish(), 1).adr, 25.25);
    }

    #[test]
    fn multipart_kast_counts_rounds_before_calculating_the_percentage() {
        let mut total = PlayerStatsAccumulator::default();
        total.add_part(
            &EventDatasets {
                kills: vec![kill(100, 2, CT, 1, T)],
                ..Default::default()
            },
            &[
                round(1, 0, 1000),
                round(2, 2000, 3000),
                round(3, 4000, 5000),
            ],
            64.0,
            true,
        );
        total.add_part(
            &EventDatasets {
                kills: vec![kill(100, 1, T, 2, CT)],
                ..Default::default()
            },
            &[round(4, 0, 1000)],
            64.0,
            true,
        );
        assert_eq!(find(&total.finish(), 1).kast, 75.0);
    }

    #[test]
    fn multipart_trades_cannot_cross_recording_boundaries() {
        let mut total = PlayerStatsAccumulator::default();
        for (number, kill) in [(1, kill(100, 2, CT, 1, T)), (2, kill(101, 3, T, 2, CT))] {
            total.add_part(
                &EventDatasets {
                    kills: vec![kill],
                    ..Default::default()
                },
                &[round(number, 0, 1000)],
                64.0,
                true,
            );
        }
        assert_eq!(find(&total.finish(), 1).traded_deaths, 0);
    }

    #[test]
    fn multipart_trailing_freeze_deaths_do_not_enter_the_last_round() {
        let mut total = PlayerStatsAccumulator::default();
        total.add_part(
            &EventDatasets {
                kills: vec![kill(100, 1, T, 2, CT), kill(1001, 1, T, 1, T)],
                ..Default::default()
            },
            &[round(1, 0, 1000)],
            64.0,
            true,
        );
        assert_eq!(find(&total.finish(), 1).deaths, 0);
    }

    #[test]
    fn multipart_restart_deaths_stay_out_of_match_totals() {
        let mut total = PlayerStatsAccumulator::default();
        for number in [1, 2] {
            total.add_part(
                &EventDatasets {
                    kills: vec![kill(9, 1, T, 1, T), kill(100, 1, T, 2, CT)],
                    ..Default::default()
                },
                &[round_with_freeze(number, 0, 50, 1000)],
                64.0,
                true,
            );
        }
        assert_eq!(find(&total.finish(), 1).deaths, 0);
    }

    #[test]
    fn multipart_knife_rounds_keep_their_exclusion_after_offsets() {
        for exclude in [false, true] {
            let mut total = PlayerStatsAccumulator::default();
            let mut knife = round(1, 0, 1000);
            knife.is_knife_round = true;
            total.add_part(
                &EventDatasets {
                    kills: vec![kill(100, 1, T, 2, CT), kill(2100, 1, T, 2, CT)],
                    ..Default::default()
                },
                &[knife, round(1, 2000, 3000)],
                64.0,
                exclude,
            );
            total.add_part(
                &EventDatasets {
                    kills: vec![kill(100, 1, T, 2, CT)],
                    ..Default::default()
                },
                &[round(2, 0, 1000)],
                64.0,
                exclude,
            );
            let expected = if exclude { 2 } else { 3 };
            assert_eq!(find(&total.finish(), 1).rounds_played, expected);
        }
    }

    #[test]
    fn recorded_and_inferred_flash_assisters_both_get_credit() {
        let blinds = [blind(50, 2.0, 4, T, 2, CT)];
        let stats = player_stats(
            &assist_kills(true),
            &[],
            &blinds,
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        for id in [3, 4] {
            assert_eq!(
                (find(&stats, id).assists, find(&stats, id).flash_assists),
                (1, 1)
            );
        }
    }

    #[test]
    fn repeated_flash_sources_do_not_duplicate_assist_credit() {
        let blinds = [
            blind(50, 2.0, 3, T, 2, CT),
            blind(50, 2.0, 4, T, 2, CT),
            blind(60, 2.0, 4, T, 2, CT),
        ];
        for recorded_flash in [false, true] {
            let stats = player_stats(
                &assist_kills(recorded_flash),
                &[],
                &blinds,
                &[],
                &[round(1, 0, 1000)],
                320,
                false,
            );
            for id in [3, 4] {
                assert_eq!(
                    (find(&stats, id).assists, find(&stats, id).flash_assists),
                    (1, 1)
                );
            }
        }
    }

    #[test]
    fn the_killer_cannot_receive_a_flash_assist() {
        let blinds = [blind(50, 2.0, 1, T, 2, CT)];
        let stats = player_stats(
            &assist_kills(false),
            &[],
            &blinds,
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        assert_eq!(find(&stats, 1).assists, 0);
    }

    #[test]
    fn self_and_team_flashes_do_not_receive_assists() {
        let blinds = [blind(50, 2.0, 2, CT, 2, CT), blind(50, 2.0, 5, CT, 2, CT)];
        let stats = player_stats(
            &assist_kills(false),
            &[],
            &blinds,
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        for id in [2, 5] {
            assert_eq!(find(&stats, id).assists, 0);
        }
    }

    #[test]
    fn inferred_flash_assists_count_toward_kast() {
        let blinds = [blind(50, 2.0, 4, T, 2, CT)];
        let stats = player_stats(
            &assist_kills(false),
            &[],
            &blinds,
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        assert_eq!(find(&stats, 4).kast, 100.0);
    }

    #[test]
    fn flash_assists_require_an_active_blind_at_the_replay_tickrate() {
        let rounds = [round(1, 0, 1000)];
        let kills = [kill(500, 1, T, 2, CT)];
        for (tick, duration, tickrate, expected) in [
            (437, 1.0, 64.0, 1),
            (436, 1.0, 64.0, 0), // expires exactly at the kill
            (400, 1.0, 64.0, 0),
            (400, 1.0, 128.0, 1),
            (501, 1.0, 64.0, 0), // starts after the kill
            (500, 1.0, 64.0, 1),
            (500, 0.0, 64.0, 0),
            (500, -1.0, 64.0, 0),
            (500, f32::NAN, 64.0, 0),
            (500, f32::INFINITY, 64.0, 0),
        ] {
            let blinds = [blind(tick, duration, 3, T, 2, CT)];
            let stats =
                player_stats_at_tickrate(&kills, &[], &blinds, &[], &rounds, 320, false, tickrate);
            assert_eq!(
                find(&stats, 3).flash_assists,
                expected,
                "{tick}, {duration}, {tickrate}"
            );
        }
    }

    #[test]
    fn flash_assists_cannot_cross_round_boundaries() {
        let rounds = [round(1, 0, 1000), round(2, 2000, 3000)];
        let stats = player_stats(
            &[kill(2200, 1, T, 2, CT)],
            &[],
            &[blind(100, 100.0, 3, T, 2, CT)],
            &[],
            &rounds,
            320,
            false,
        );
        assert_eq!(find(&stats, 3).flash_assists, 0);
    }

    #[test]
    fn flash_assists_require_the_same_full_pawn_identity() {
        let kills = [Kill {
            victim_entity_id: Some(10),
            victim_entity_serial: Some(7),
            ..kill(2200, 1, T, 2, CT)
        }];
        for (index, serial, expected) in [(10, 6, 0), (11, 7, 0), (10, 7, 1)] {
            let blinds = [Blind {
                victim_entity_id: Some(index),
                victim_entity_serial: Some(serial),
                ..blind(2150, 100.0, 3, T, 2, CT)
            }];
            let stats = player_stats(
                &kills,
                &[],
                &blinds,
                &[],
                &[round(1, 2000, 3000)],
                320,
                false,
            );
            assert_eq!(find(&stats, 3).flash_assists, expected);
        }
    }

    #[test]
    fn excluded_knife_rounds_do_not_produce_player_stats() {
        let mut knife_round = round(1, 2000, 3000);
        knife_round.is_knife_round = true;
        let stats = player_stats(
            &[kill(2200, 1, T, 2, CT)],
            &[],
            &[blind(2150, 2.0, 3, T, 2, CT)],
            &[],
            &[knife_round],
            320,
            true,
        );
        assert!(stats.is_empty());
    }

    fn opening_round_stats() -> Vec<PlayerStats> {
        let rounds = [round(1, 0, 1000), round(2, 2000, 3000)];
        let kills = [
            kill(100, 4, CT, 1, T),
            kill(200, 1, T, 5, CT),
            kill(250, 1, T, 6, CT),
            kill(300, 1, T, 7, CT),
        ];
        player_stats(&kills, &[], &[], &[], &rounds, 320, false)
    }

    #[test]
    fn opening_stats_credit_only_the_first_kill_and_death() {
        let stats = opening_round_stats();
        assert_eq!(find(&stats, 4).opening_kills, 1);
        assert_eq!(find(&stats, 1).opening_deaths, 1);
    }

    #[test]
    fn triple_kills_count_as_one_three_kill_round() {
        let stats = opening_round_stats();
        let player = find(&stats, 1);
        assert_eq!(
            (player.kills, player.multikill_3k, player.multikill_2k),
            (3, 1, 0)
        );
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

    fn damage(tick: i32, attacker: u64, amount: i32, health_post: i32) -> Damage {
        Damage {
            tick,
            attacker_steamid: Some(attacker),
            attacker_side: Some(T.into()),
            victim_steamid: Some(5),
            victim_side: Some(CT.into()),
            dmg_health: amount,
            health_pre: (health_post + amount).min(100),
            health_post,
            ..Default::default()
        }
    }

    #[test]
    fn adr_does_not_credit_health_rounding() {
        // HOTU–Astralis Ancient, round 2: mizu has 57 HP before Staehr's
        // 35-damage hit at tick 10711, which reports 21 HP afterward.
        let damages = [damage(100, 1, 43, 57), damage(10711, 1, 35, 21)];
        let stats = player_stats(&[], &damages, &[], &[], &[round(2, 0, 12000)], 320, false);
        assert_eq!(find(&stats, 1).adr, 78.0);
    }

    #[test]
    fn adr_caps_same_tick_shotgun_pellets() {
        let damages = [damage(100, 1, 79, 21), damage(100, 1, 79, 0)];
        let stats = player_stats(&[], &damages, &[], &[], &[round(1, 0, 1000)], 320, false);
        assert_eq!(find(&stats, 1).adr, 100.0);
    }

    #[test]
    fn adr_caps_same_tick_damage_from_different_attackers() {
        let damages = [
            damage(50, 1, 31, 69),
            damage(100, 2, 9, 60),
            damage(100, 1, 128, 0),
        ];
        let stats = player_stats(&[], &damages, &[], &[], &[round(1, 0, 1000)], 320, false);
        assert_eq!(find(&stats, 1).adr, 91.0); // 31 + the remaining 60 HP
    }

    #[test]
    fn adr_uses_reported_health_after_excluded_damage() {
        let damages = [
            Damage {
                attacker_steamid: None,
                attacker_side: None,
                ..damage(50, 1, 30, 69)
            },
            damage(100, 1, 128, 0),
        ];
        let stats = player_stats(&[], &damages, &[], &[], &[round(1, 0, 1000)], 320, false);
        assert_eq!(find(&stats, 1).adr, 69.0);
    }

    #[test]
    fn adr_does_not_credit_zero_reported_damage() {
        let stats = player_stats(
            &[],
            &[damage(100, 1, 0, 99)],
            &[],
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        assert_eq!(find(&stats, 1).adr, 0.0);
    }

    #[test]
    fn adr_ignores_negative_reported_damage() {
        let stats = player_stats(
            &[],
            &[damage(100, 1, -1, 99)],
            &[],
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        assert_eq!(find(&stats, 1).adr, 0.0);
    }

    #[test]
    fn adr_resets_remaining_health_each_round() {
        let damages = [damage(100, 1, 90, 10), damage(2100, 1, 90, 10)];
        let rounds = [round(1, 0, 1000), round(2, 2000, 3000)];
        let stats = player_stats(&[], &damages, &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats, 1).adr, 90.0);
    }

    #[test]
    fn adr_caps_unresolved_victims_using_the_per_event_estimate() {
        let damages = [Damage {
            victim_steamid: None,
            ..damage(100, 1, 128, 0)
        }];
        let stats = player_stats(&[], &damages, &[], &[], &[round(1, 0, 1000)], 320, false);
        assert_eq!(find(&stats, 1).adr, 100.0);
    }

    #[test]
    fn utility_damage_does_not_credit_health_rounding() {
        let damages = [Damage {
            weapon: "inferno".into(),
            ..damage(100, 1, 6, 93)
        }];
        let stats = player_stats(&[], &damages, &[], &[], &[round(1, 0, 1000)], 320, false);
        assert_eq!(find(&stats, 1).utility_damage, 6);
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
            dmg_health: pre - post,
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

    const T: &str = "terrorist";
    const CT: &str = "counter-terrorist";

    /// A round won by `winner`, so clutch outcomes can be set up explicitly.
    fn round_won_by(num: i32, start: i32, end: i32, winner: &str) -> Round {
        Round {
            winner_side: winner.into(),
            ..round(num, start, end)
        }
    }

    /// Damage rows that put each of `ids` on `side` at `tick` without anyone
    /// dying — the cheapest way to make a round's rosters known. The victim is
    /// left unresolved so these contribute no ADR.
    fn seed(tick: i32, side: &str, ids: &[u64]) -> Vec<Damage> {
        ids.iter()
            .map(|&id| Damage {
                tick,
                attacker_steamid: Some(id),
                attacker_side: Some(side.into()),
                health_pre: 100,
                health_post: 100,
                ..Default::default()
            })
            .collect()
    }

    /// Both sides' rosters, seeded at `tick`.
    fn seed_both(tick: i32, terrorists: &[u64], cts: &[u64]) -> Vec<Damage> {
        let mut out = seed(tick, T, terrorists);
        out.extend(seed(tick, CT, cts));
        out
    }

    #[test]
    fn last_player_alive_against_two_is_a_1v2() {
        // 3v2. T 1 and T 2 die, leaving T 3 against CT 11 and CT 12 — and T wins.
        let rounds = vec![round_won_by(1, 0, 1000, T)];
        let damages = seed_both(10, &[1, 2, 3], &[11, 12]);
        let kills = vec![
            kill(100, 11, CT, 1, T),
            kill(200, 11, CT, 2, T),
            // T 3 clutches it out.
            kill(300, 3, T, 11, CT),
        ];
        let stats = player_stats(&kills, &damages, &[], &[], &rounds, 320, false);

        let p3 = find(&stats, 3);
        assert_eq!(p3.clutches_played, 1);
        assert_eq!(p3.clutches_won, 1);
        // Fixed at the moment they were left alone: both CTs were still up, so
        // this stays a 1v2 even though they only had to kill one of them.
        assert_eq!(p3.clutch_1v2, 1);
        assert_eq!(p3.clutch_1v1, 0);
        // Their teammates were not in the clutch.
        assert_eq!(find(&stats, 1).clutches_played, 0);
    }

    #[test]
    fn a_lost_clutch_counts_as_played_but_not_won() {
        let rounds = vec![round_won_by(1, 0, 1000, CT)]; // CT take the round
        let damages = seed_both(10, &[1, 2, 3], &[11, 12, 13]);
        let kills = vec![kill(100, 11, CT, 1, T), kill(200, 11, CT, 2, T)];
        let stats = player_stats(&kills, &damages, &[], &[], &rounds, 320, false);

        let p3 = find(&stats, 3);
        assert_eq!(p3.clutches_played, 1);
        assert_eq!(p3.clutches_won, 0);
        // Only wins are bucketed by opponent count.
        assert_eq!(p3.clutch_1v3, 0);
    }

    #[test]
    fn a_quiet_round_is_filled_in_from_the_rounds_around_it() {
        // T 3 does nothing at all in round 2 — no kill, no death, no damage. They
        // are still alive, so T 2 surviving alongside them is not a clutch.
        let rounds = vec![
            round_won_by(1, 0, 1000, T),
            round_won_by(2, 2000, 3000, T),
            round_won_by(3, 4000, 5000, T),
        ];
        let mut damages = seed_both(10, &[1, 2, 3], &[11, 12]);
        damages.extend(seed_both(4010, &[1, 2, 3], &[11, 12]));
        let kills = vec![kill(2100, 11, CT, 1, T)];

        let starts = round_starts(&rounds);
        let obs = side_observations(&kills, &damages, &[], &[], &starts, &[]);
        let rosters = round_rosters(&obs, rounds.len());
        // Round 2 has no evidence for player 3, but they are mid-match.
        assert!(rosters[1][T].contains(&3));

        let stats = player_stats(&kills, &damages, &[], &[], &rounds, 320, false);
        assert!(stats.iter().all(|s| s.clutches_played == 0));
    }

    #[test]
    fn becoming_last_alive_is_required() {
        // T fields a single player from the round's first tick, so they never
        // *become* last alive and are not scored as a clutch. CT, who go from two
        // players to one, are.
        let rounds = vec![round_won_by(1, 0, 1000, T)];
        let damages = seed_both(10, &[1], &[11, 12]);
        let kills = vec![kill(100, 1, T, 11, CT)];
        let stats = player_stats(&kills, &damages, &[], &[], &rounds, 320, false);
        assert_eq!(find(&stats, 1).clutches_played, 0);
        assert_eq!(find(&stats, 12).clutches_played, 1);
    }

    #[test]
    fn rosters_follow_the_halftime_swap() {
        // Rounds 1-2: ids 1-2 are T, 11-12 are CT. Rounds 3-4: they swap. Round
        // 4's roster must use their *second-half* sides.
        let rounds = vec![
            round_won_by(1, 0, 1000, T),
            round_won_by(2, 2000, 3000, T),
            round_won_by(3, 4000, 5000, T),
            round_won_by(4, 6000, 7000, CT),
        ];
        let mut damages = seed_both(10, &[1, 2], &[11, 12]);
        damages.extend(seed_both(2010, &[1, 2], &[11, 12]));
        // Halftime: 1 and 2 are now CT, 11 and 12 are now T.
        damages.extend(seed_both(4010, &[11, 12], &[1, 2]));
        damages.extend(seed_both(6010, &[11, 12], &[1, 2]));
        // Round 4: T 11 dies, leaving T 12 alone against CT 1 and CT 2.
        let kills = vec![kill(6100, 1, CT, 11, T)];

        let starts = round_starts(&rounds);
        let obs = side_observations(&kills, &damages, &[], &[], &starts, &[]);
        assert_eq!(halves(&obs, rounds.len()), vec![0, 0, 1, 1]);

        let rosters = round_rosters(&obs, rounds.len());
        assert_eq!(rosters[0][T], HashSet::from([1, 2]));
        assert_eq!(rosters[3][T], HashSet::from([11, 12]));
        assert_eq!(rosters[3][CT], HashSet::from([1, 2]));

        let stats = player_stats(&kills, &damages, &[], &[], &rounds, 320, false);
        let p12 = find(&stats, 12);
        assert_eq!(p12.clutches_played, 1);
        assert_eq!(p12.clutches_won, 0); // CT won round 4
    }

    #[test]
    fn players_are_only_rostered_while_they_are_in_the_match() {
        // Someone who first appears in round 3 must not be counted alive in
        // rounds 1-2, and someone last seen in round 1 must not linger.
        let rounds = vec![
            round_won_by(1, 0, 1000, T),
            round_won_by(2, 2000, 3000, T),
            round_won_by(3, 4000, 5000, T),
        ];
        let mut damages = seed_both(10, &[1], &[11]); // round 1 only
        damages.extend(seed_both(4010, &[2], &[12])); // join in round 3

        let starts = round_starts(&rounds);
        let obs = side_observations(&[], &damages, &[], &[], &starts, &[]);
        let rosters = round_rosters(&obs, rounds.len());
        assert_eq!(rosters[0][T], HashSet::from([1]));
        assert_eq!(rosters[2][T], HashSet::from([2]));
        // The round-3 arrivals are absent from round 1 entirely.
        assert!(rosters[0].get(CT).is_none_or(|ct| !ct.contains(&12)));
        // ... and round 1's players are gone by round 3.
        assert!(!rosters[2][T].contains(&1));
    }

    fn competing_trade_kills() -> [Kill; 4] {
        [
            kill(100, 11, CT, 1, T),
            kill(150, 11, CT, 3, T),
            kill(200, 2, T, 11, CT),
            kill(400, 12, CT, 2, T),
        ]
    }

    #[test]
    fn traded_death_totals_agree_with_the_kills_dataset() {
        let kills = competing_trade_kills();
        let flags = trade_flags(&kills, 320);
        let stats = player_stats(&kills, &[], &[], &[], &[round(1, 0, 1000)], 320, false);
        let tallied: i32 = stats.iter().map(|s| s.traded_deaths).sum();
        assert_eq!(
            tallied,
            flags.iter().filter(|(_, traded)| *traded).count() as i32
        );
        assert_eq!(
            (find(&stats, 1).traded_deaths, find(&stats, 3).traded_deaths),
            (1, 0)
        );
    }

    #[test]
    fn only_the_matched_trade_victim_gets_kast_credit() {
        let stats = player_stats(
            &competing_trade_kills(),
            &[],
            &[],
            &[],
            &[round(1, 0, 1000)],
            320,
            false,
        );
        assert_eq!((find(&stats, 1).kast, find(&stats, 3).kast), (100.0, 0.0));
    }
}
