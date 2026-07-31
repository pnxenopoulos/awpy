//! Higher-level, structured datasets built on top of the raw parser.
//!
//! These turn the low-level event and entity streams into the tables analysts
//! usually want:
//!
//! - [`Parser::rounds`] — one row per round, reconstructed from the
//!   `CCSGameRules` entity state (start / freeze-end / end ticks, winning side,
//!   and end reason). This is robust to demos that do not emit `round_start` /
//!   `round_end` game events (many competitive CS2 demos don't).
//! - [`Parser::kills`] / [`Parser::damages`] — one row per `player_death` /
//!   `player_hurt` event, with each participant resolved to a Steam id, name,
//!   side, and world position.
//! - [`Parser::bomb`] — bomb actions (pickup / drop / plant / defuse).
//! - [`Parser::grenades`] — thrown-grenade trajectories.
//! - [`Parser::fires`] / [`Parser::smokes`] — active infernos / smoke clouds.
//! - [`Parser::shots`] — `weapon_fire` events with shooter and weapon state.
//! - [`Parser::players`] — the roster (Steam id, name, last observed side).
//! - [`Parser::snapshot`] / [`Parser::snapshots_query`] — per-player game state
//!   (position, eye angles, health, armor, and economy: equipment value,
//!   primary / secondary weapon, grenade counts, and inventory) at a tick or
//!   over a tick range.
//! - [`Parser::blinds`] — flash events (who was blinded, by whom, for how long),
//!   reconstructed from pawn flash state and `flashbang_detonate`.
//! - [`Parser::chat`] — chat messages, decoded from `SayText` user messages.

use std::collections::{HashMap, HashSet};

use crate::demo::{Context, GameEvent, Parser};
use crate::entity::Entity;
use crate::error::Result;
use crate::hitgroups::hitgroup_name;
use crate::position::cell_to_world;
use crate::round_end_reasons::round_end_reason_name;
use crate::teams::team_name;
use crate::weapons::{
    WeaponSlot, grenade_projectile_classes, grenade_type, weapon_classes, weapon_info,
};

/// User-id sentinel meaning "no such player" (e.g. no assister).
const NO_USER_ID: i32 = 65535;

/// Maximum player health / armor, used to clamp reconstructed pre-hit values.
const MAX_HEALTH: i32 = 100;
const MAX_ARMOR: i32 = 100;

/// The game-rules entity whose state drives [`Parser::rounds`].
const GAME_RULES_CLASS: &str = "CCSGameRulesProxy";

/// Upper bound on inventory slots read from a pawn's loadout vector, capping the
/// networked element count defensively. A real loadout never approaches this.
const MAX_INVENTORY: usize = 64;

/// `m_fFlags` bit set while the player is standing on the ground (Source
/// `FL_ONGROUND`); cleared when airborne.
const FL_ONGROUND: u32 = 1;

/// Team round-start equipment value below which the team is playing an "eco".
const BUY_ECO_MAX: i32 = 5_000;
/// Team round-start equipment value at or above which it is a "full" buy.
const BUY_FULL_MIN: i32 = 20_000;

/// Classify a team's total round-start equipment value into a buy type:
/// `"eco"` (saving), `"force"` (partial buy), or `"full"`. Pistol rounds are
/// labelled `"pistol"` by the caller, ahead of any value classification.
fn buy_type(team_equipment: i32) -> &'static str {
    if team_equipment < BUY_ECO_MAX {
        "eco"
    } else if team_equipment < BUY_FULL_MIN {
        "force"
    } else {
        "full"
    }
}

/// Whether most players shared between two rounds are on the opposite side in the
/// later round — the tell-tale of a halftime side switch.
fn sides_flipped(prev: &HashMap<u64, &str>, cur: &HashMap<u64, &str>) -> bool {
    let (mut flipped, mut same) = (0, 0);
    for (steamid, &cur_side) in cur {
        if let Some(&prev_side) = prev.get(steamid) {
            if prev_side == cur_side {
                same += 1;
            } else {
                flipped += 1;
            }
        }
    }
    flipped > same
}

/// Upper bound on a single purchase's money cost. A larger drop is a money
/// reset (match start / halftime), not a buy — no single loadout costs this much.
const MAX_PURCHASE_COST: i32 = 6500;

/// Free default-loadout items that can never be purchased (the side pistols and
/// the bomb). Their round-start grant coincides with a money reset, so without
/// this they would masquerade as buys.
const FREE_DEFAULT_ITEMS: &[&str] = &["glock", "usp_silencer", "hkp2000", "c4"];

/// A pawn's `m_flFlashDuration` must exceed this (in seconds) to count as a
/// blind — filters out negligible flashes and float noise near zero.
const FLASH_MIN_DURATION: f32 = 0.1;
/// A rising edge of at least this many seconds marks a *new* blind, so a
/// re-flash mid-blind is caught while the (non-increasing) decay of an existing
/// flash is not.
const FLASH_EDGE_MARGIN: f32 = 0.05;

/// Player pawn entity — carries position, side, and a handle to the controller.
const PLAYER_PAWN_CLASS: &str = "CCSPlayerPawn";
/// Player controller entity — carries the persistent Steam id and name.
const PLAYER_CONTROLLER_CLASS: &str = "CCSPlayerController";
/// Team entity — one per team number, carrying the organization ("clan") name.
const TEAM_CLASS: &str = "CCSTeam";
/// Planted-bomb entity — carries the bomb-site index while the bomb is down.
const PLANTED_C4_CLASS: &str = "CPlantedC4";

/// Burning-inferno entity (molotov / incendiary), tracked by [`Parser::fires`].
const INFERNO_CLASS: &str = "CInferno";
/// Smoke-cloud projectile entity, tracked by [`Parser::smokes`].
const SMOKE_CLASS: &str = "CSmokeGrenadeProjectile";

/// `(game event, dataset label)` for the [`Parser::bomb`] dataset.
const BOMB_EVENTS: &[(&str, &str)] = &[
    ("bomb_pickup", "pickup"),
    ("bomb_dropped", "drop"),
    ("bomb_beginplant", "start_plant"),
    ("bomb_abortplant", "interrupt_plant"),
    ("bomb_planted", "finish_plant"),
    ("bomb_defused", "defuse"),
];

/// Dotted field-path prefix for a pawn's networked world position.
const ORIGIN_PATH: &str = "CBodyComponent.m_skeletonInstance.m_vecOrigin";

/// A small view over a game event's `(key, value)` pairs with typed getters.
///
/// Values arrive as strings from the Source 1 legacy game-event decoding;
/// missing keys and unparseable values fall back to the type's default.
struct Keys<'a>(&'a [(String, String)]);

impl<'a> Keys<'a> {
    fn get(&self, key: &str) -> Option<&str> {
        self.0
            .iter()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v.as_str())
    }

    fn i32(&self, key: &str) -> i32 {
        self.get(key).and_then(|s| s.parse().ok()).unwrap_or(0)
    }

    fn i64(&self, key: &str) -> i64 {
        self.get(key).and_then(|s| s.parse().ok()).unwrap_or(0)
    }

    fn f32(&self, key: &str) -> Option<f32> {
        self.get(key).and_then(|s| s.parse().ok())
    }

    fn bool(&self, key: &str) -> bool {
        self.get(key) == Some("true")
    }

    fn string(&self, key: &str) -> String {
        self.get(key).unwrap_or_default().to_string()
    }
}

/// A single round, reconstructed from `CCSGameRules` state transitions.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Round {
    /// 1-indexed round number (the value of `m_totalRoundsPlayed` at round end).
    pub round_num: i32,
    /// Tick the round's freeze time began (`None` if not observed, e.g. a demo
    /// that starts mid-round).
    pub start_tick: Option<i32>,
    /// Tick freeze time ended and play began (`None` if not observed).
    pub freeze_end_tick: Option<i32>,
    /// Tick the round was decided (a winner was set).
    pub end_tick: i32,
    /// Tick the round *officially* ended — the post-round period after the
    /// winner is decided, taken as the start of the next round's freeze time.
    /// `None` for the final round (no next round follows).
    pub official_end_tick: Option<i32>,
    /// Winning team number (2 = terrorist, 3 = counter-terrorist).
    pub winner: i32,
    /// Winning side name (see [`team_name`]).
    pub winner_side: String,
    /// Raw round-end reason code (`RoundEndReason_t`).
    pub reason: i32,
    /// Human-readable round-end reason (see [`round_end_reason_name`]).
    pub reason_name: String,
    /// Whether this is a knife round — a side-decider round in which every kill
    /// is a melee (knife) kill, with no firearm or grenade kills. These do not
    /// count toward the score and are excluded from [`Parser::player_stats`] by
    /// default.
    pub is_knife_round: bool,
}

/// A single kill, from a `player_death` game event, enriched with each resolved
/// participant — Steam id, name, side, and world position `(x, y, z)` at the
/// kill tick — for the attacker, victim, and assister.
///
/// A participant's fields are all `None` when that participant is absent (no
/// assister) or could not be resolved from entity state (e.g. a world kill).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct Kill {
    pub tick: i32,

    pub attacker_steamid: Option<u64>,
    pub attacker_name: Option<String>,
    pub attacker_side: Option<String>,
    pub attacker_x: Option<f32>,
    pub attacker_y: Option<f32>,
    pub attacker_z: Option<f32>,

    pub victim_steamid: Option<u64>,
    pub victim_name: Option<String>,
    pub victim_side: Option<String>,
    pub victim_x: Option<f32>,
    pub victim_y: Option<f32>,
    pub victim_z: Option<f32>,

    pub assister_steamid: Option<u64>,
    pub assister_name: Option<String>,
    pub assister_side: Option<String>,
    pub assister_x: Option<f32>,
    pub assister_y: Option<f32>,
    pub assister_z: Option<f32>,

    pub weapon: String,
    pub headshot: bool,
    /// Whether the assist was a flash assist (assister blinded the victim).
    pub assist_flash: bool,
    pub dominated: i32,
    pub noscope: bool,
    pub penetrated: i32,
    pub revenge: i32,
    pub thrusmoke: bool,
    pub hitgroup: i32,
    pub hitgroup_name: String,

    /// Whether this kill **is** a trade — the attacker killed someone who had
    /// just killed one of the attacker's teammates, within the trade window.
    /// See [`trade_flags`].
    pub is_trade: bool,
    /// Whether this kill's **victim was traded** — a teammate of the victim
    /// killed this attacker within the trade window. This is the flag behind
    /// [`PlayerStats::traded_deaths`](crate::stats::PlayerStats::traded_deaths).
    pub victim_traded: bool,
}

/// Default trade window in seconds — how long after a death a teammate's
/// revenge kill still counts as a trade.
pub const TRADE_SECONDS: f32 = 5.0;

/// Classify every kill as a trade and/or a traded death.
///
/// A death is **traded** when the killer is themselves killed by a teammate of
/// the victim within `trade_ticks`. The revenge kill **is a trade**. The two
/// flags are duals: whenever kill *A* has `victim_traded`, the kill *B* that
/// avenged it has `is_trade`.
///
/// Returns `(is_trade, victim_traded)` per kill, positionally matching `kills`
/// (which need not be sorted). A kill with an unresolved attacker or victim side
/// can neither trade nor be traded, since there is no team to compare against.
///
/// The two flags do not occur in equal numbers: one kill can avenge several
/// teammates at once — a player who kills two enemies and is then killed by a
/// third trades both of those deaths — so `victim_traded` is usually the more
/// common of the two.
pub fn trade_flags(kills: &[Kill], trade_ticks: i32) -> Vec<(bool, bool)> {
    let mut flags = vec![(false, false); kills.len()];

    // Indices in tick order, so the window scan can stop at the first kill past
    // the window instead of walking the whole match.
    let mut order: Vec<usize> = (0..kills.len()).collect();
    order.sort_by_key(|&i| kills[i].tick);

    for (pos, &i) in order.iter().enumerate() {
        let death = &kills[i];
        // The killer, who a teammate of the victim must kill for this to trade.
        let Some(killer) = death.attacker_steamid else {
            continue;
        };
        let Some(victim_side) = &death.victim_side else {
            continue;
        };
        for &j in &order[pos + 1..] {
            let revenge = &kills[j];
            if revenge.tick - death.tick > trade_ticks {
                break;
            }
            if revenge.tick > death.tick
                && revenge.victim_steamid == Some(killer)
                && revenge.attacker_side.as_ref() == Some(victim_side)
            {
                flags[i].1 = true; // this death was traded
                flags[j].0 = true; // and that kill is the trade
                break;
            }
        }
    }
    flags
}

/// A single damage instance, from a `player_hurt` game event, enriched with the
/// resolved attacker and victim (Steam id, name, side, world position) and the
/// victim's health/armor before and after the hit.
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct Damage {
    pub tick: i32,

    pub attacker_steamid: Option<u64>,
    pub attacker_name: Option<String>,
    pub attacker_side: Option<String>,
    pub attacker_x: Option<f32>,
    pub attacker_y: Option<f32>,
    pub attacker_z: Option<f32>,

    pub victim_steamid: Option<u64>,
    pub victim_name: Option<String>,
    pub victim_side: Option<String>,
    pub victim_x: Option<f32>,
    pub victim_y: Option<f32>,
    pub victim_z: Option<f32>,

    pub weapon: String,
    pub dmg_health: i32,
    pub dmg_armor: i32,
    pub hitgroup: i32,
    pub hitgroup_name: String,
    /// Victim health before the hit (`health_post + dmg_health`).
    pub health_pre: i32,
    /// Victim health after the hit (the event's `health`).
    pub health_post: i32,
    /// Victim armor before the hit (`armor_post + dmg_armor`).
    pub armor_pre: i32,
    /// Victim armor after the hit (the event's `armor`).
    pub armor_post: i32,
}

/// Build a [`Damage`] from a `player_hurt` event's own fields, leaving the
/// resolved-player fields at their defaults (filled in later from entities).
fn damage_event_fields(e: &GameEvent) -> Damage {
    let k = Keys(&e.keys);
    let hitgroup = k.i32("hitgroup");
    let dmg_health = k.i32("dmg_health");
    let dmg_armor = k.i32("dmg_armor");
    let health_post = k.i32("health");
    let armor_post = k.i32("armor");
    Damage {
        tick: e.tick,
        weapon: k.string("weapon"),
        dmg_health,
        dmg_armor,
        hitgroup,
        hitgroup_name: hitgroup_name(hitgroup as i64).to_string(),
        health_post,
        // `dmg_health` is the raw, uncapped damage and can exceed the victim's
        // health (a lethal overkill hit), so clamp the reconstructed pre-health
        // to the 100 HP / armor maximum.
        health_pre: (health_post + dmg_health).min(MAX_HEALTH),
        armor_post,
        armor_pre: (armor_post + dmg_armor).min(MAX_ARMOR),
        ..Default::default()
    }
}

/// A single bomb action (pickup / drop / plant / defuse), with the acting
/// player and their position. See [`Parser::bomb`].
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct BombEvent {
    pub tick: i32,
    /// One of `pickup`, `drop`, `start_plant`, `interrupt_plant`,
    /// `finish_plant`, `defuse`.
    pub event: String,
    pub steamid: Option<u64>,
    pub name: Option<String>,
    /// `A` / `B` while a bomb is planted (from `CPlantedC4.m_nBombSite`); `None`
    /// for pre-plant actions.
    pub bombsite: Option<String>,
    pub x: Option<f32>,
    pub y: Option<f32>,
    pub z: Option<f32>,
}

/// One sample of a thrown grenade's trajectory (one row per tick the projectile
/// is live). See [`Parser::grenades`].
#[derive(Debug, Clone, serde::Serialize)]
pub struct Grenade {
    pub tick: i32,
    pub thrower_name: Option<String>,
    pub thrower_steamid: Option<u64>,
    pub thrower_side: Option<String>,
    #[serde(rename = "type")]
    pub grenade_type: String,
    pub entity_id: i32,
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

/// A single burning inferno (molotov / incendiary): one row per fire, with its
/// landing position, thrower, and burn window `[start_tick, end_tick]`. See
/// [`Parser::fires`].
#[derive(Debug, Clone, serde::Serialize)]
pub struct Fire {
    pub start_tick: i32,
    pub end_tick: i32,
    pub thrower_name: Option<String>,
    pub thrower_steamid: Option<u64>,
    pub thrower_side: Option<String>,
    #[serde(rename = "type")]
    pub fire_type: String,
    pub entity_id: i32,
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

/// A single deployed smoke cloud: one row per smoke, with its position, thrower,
/// and active window `[start_tick, end_tick]`. See [`Parser::smokes`].
#[derive(Debug, Clone, serde::Serialize)]
pub struct Smoke {
    pub start_tick: i32,
    pub end_tick: i32,
    pub thrower_name: Option<String>,
    pub thrower_steamid: Option<u64>,
    pub thrower_side: Option<String>,
    pub entity_id: i32,
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

/// A single shot fired (`weapon_fire` game event), with the shooter's state and
/// active-weapon state at the shot tick. See [`Parser::shots`].
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct Shot {
    pub tick: i32,
    pub steamid: Option<u64>,
    pub name: Option<String>,
    pub side: Option<String>,
    pub x: Option<f32>,
    pub y: Option<f32>,
    pub z: Option<f32>,
    pub pitch: Option<f32>,
    pub yaw: Option<f32>,
    pub weapon: String,
    pub scoped: Option<bool>,
    /// Networked accuracy penalty of the active weapon (a proxy for inaccuracy;
    /// CS2 does not network the fully-computed inaccuracy).
    pub inaccuracy: Option<f32>,
    pub num_bullets_remaining: Option<i32>,
}

/// Internal per-tick sample used by the projectile-tracking datasets.
struct TrackedRow {
    tick: i32,
    entity_id: i32,
    class_name: String,
    x: f32,
    y: f32,
    z: f32,
    thrower: ResolvedPlayer,
    start_tick: i32,
    end_tick: i32,
}

/// Collapse per-tick projectile samples to one row per instance, keyed by
/// `(entity index, start tick)`.
///
/// Used by the *static* trackers (fires, smokes) where an instance holds one
/// position for its whole lifetime, so the per-tick rows are redundant. The
/// thrower is resolved every tick and can degrade to `None` mid-lifetime (e.g.
/// the thrower dies and their pawn stops resolving), so the first row with a
/// resolved Steam id wins; the end tick is the latest seen. Instances keep
/// first-seen (chronological) order.
fn collapse_instances(rows: Vec<TrackedRow>) -> Vec<TrackedRow> {
    let mut order: Vec<(i32, i32)> = Vec::new();
    let mut by_key: HashMap<(i32, i32), TrackedRow> = HashMap::new();
    for row in rows {
        let key = (row.entity_id, row.start_tick);
        match by_key.get_mut(&key) {
            None => {
                order.push(key);
                by_key.insert(key, row);
            }
            Some(kept) => {
                kept.end_tick = kept.end_tick.max(row.end_tick);
                // Recover the thrower from an earlier tick if the kept row's
                // resolution had already degraded to None.
                if kept.thrower.steamid.is_none() && row.thrower.steamid.is_some() {
                    kept.thrower = row.thrower;
                }
            }
        }
    }
    order
        .into_iter()
        .map(|key| by_key.remove(&key).expect("key inserted above"))
        .collect()
}

/// Which projectile dataset a tracked row belongs to. One entity class can feed
/// more than one — a `CSmokeGrenadeProjectile` is both a grenade (its throw) and
/// a smoke (its cloud) — so trackers are tagged with their destination.
#[derive(Clone, Copy)]
enum ProjKind {
    Grenade,
    Fire,
    Smoke,
}

/// How a projectile class is tracked by [`Parser::track_projectiles`].
enum ProjMode<'a> {
    /// Grenades: emit a row while the projectile is moving; the instance's
    /// lifetime is derived from when its entity index is present.
    Trajectory,
    /// Fires / smokes: emit only while the tick is inside an event-derived
    /// active window, which also supplies the instance's `[start, end]`.
    Windowed(&'a HashMap<i32, Vec<(i32, i32)>>),
}

/// The three projectile datasets ([`Parser::grenades`], [`Parser::fires`],
/// [`Parser::smokes`]), built together in one pass by
/// [`Parser::projectiles`].
pub struct Projectiles {
    pub grenades: Vec<Grenade>,
    pub fires: Vec<Fire>,
    pub smokes: Vec<Smoke>,
}

/// Fill each trajectory instance's `end_tick` from the last tick its entity
/// index was seen (grenades have no event window to bound them).
fn fill_trajectory_ends(rows: &mut [TrackedRow]) {
    let mut ends: HashMap<(i32, i32), i32> = HashMap::new();
    for r in rows.iter() {
        let e = ends.entry((r.entity_id, r.start_tick)).or_insert(r.tick);
        *e = (*e).max(r.tick);
    }
    for r in rows.iter_mut() {
        r.end_tick = ends[&(r.entity_id, r.start_tick)];
    }
}

/// A player resolved from entity state at a given tick. All fields are `None`
/// when the participant is absent or could not be resolved.
#[derive(Default, Clone)]
struct ResolvedPlayer {
    steamid: Option<u64>,
    name: Option<String>,
    side: Option<String>,
    x: Option<f32>,
    y: Option<f32>,
    z: Option<f32>,
}

impl ResolvedPlayer {
    /// Move the resolved fields into a row's `{prefix}_steamid/name/side/x/y/z`.
    #[allow(clippy::too_many_arguments)]
    fn assign_to(
        self,
        steamid: &mut Option<u64>,
        name: &mut Option<String>,
        side: &mut Option<String>,
        x: &mut Option<f32>,
        y: &mut Option<f32>,
        z: &mut Option<f32>,
    ) {
        *steamid = self.steamid;
        *name = self.name;
        *side = self.side;
        *x = self.x;
        *y = self.y;
        *z = self.z;
    }
}

/// Build a [`Kill`] from a `player_death` event's own fields, leaving the
/// resolved-player fields at their defaults (filled in later from entities).
fn kill_event_fields(e: &GameEvent) -> Kill {
    let k = Keys(&e.keys);
    let hitgroup = k.i32("hitgroup");
    Kill {
        tick: e.tick,
        weapon: k.string("weapon"),
        headshot: k.bool("headshot"),
        assist_flash: k.bool("assistedflash"),
        dominated: k.i32("dominated"),
        noscope: k.bool("noscope"),
        penetrated: k.i32("penetrated"),
        revenge: k.i32("revenge"),
        thrusmoke: k.bool("thrusmoke"),
        hitgroup,
        hitgroup_name: hitgroup_name(hitgroup as i64).to_string(),
        ..Default::default()
    }
}

/// Cell + in-cell-offset field keys for an entity's networked world position
/// (any entity with the standard body-component scene node — pawns, grenade
/// projectiles, infernos). Resolved once per serializer.
struct PositionKeys {
    cell: [Option<u64>; 3],
    offset: [Option<u64>; 3],
}

impl PositionKeys {
    fn resolve(ser: &crate::entity::Serializer) -> Self {
        let key = |name: &str| ser.resolve_field_key(name);
        Self {
            cell: [
                key(&format!("{ORIGIN_PATH}.m_cellX")),
                key(&format!("{ORIGIN_PATH}.m_cellY")),
                key(&format!("{ORIGIN_PATH}.m_cellZ")),
            ],
            offset: [
                key(&format!("{ORIGIN_PATH}.m_vecX")),
                key(&format!("{ORIGIN_PATH}.m_vecY")),
                key(&format!("{ORIGIN_PATH}.m_vecZ")),
            ],
        }
    }

    /// World position `(x, y, z)`, or `None` if the entity has no origin set.
    fn world(&self, e: &Entity) -> Option<(f32, f32, f32)> {
        if !self.offset[0].is_some_and(|k| e.fields.contains_key(&k)) {
            return None;
        }
        let coord =
            |i: usize| cell_to_world(e.get_i64(self.cell[i]) as i32, e.get_f32(self.offset[i]));
        Some((coord(0), coord(1), coord(2)))
    }
}

/// Field keys on the `CCSPlayerPawn` serializer, resolved once.
struct PawnKeys {
    cell: [Option<u64>; 3],
    offset: [Option<u64>; 3],
    team: Option<u64>,
    controller: Option<u64>,
}

impl PawnKeys {
    fn resolve(ctx: &Context) -> Self {
        let ser = ctx.serializers.get(PLAYER_PAWN_CLASS);
        let key = |name: &str| ser.and_then(|s| s.resolve_field_key(name));
        Self {
            cell: [
                key(&format!("{ORIGIN_PATH}.m_cellX")),
                key(&format!("{ORIGIN_PATH}.m_cellY")),
                key(&format!("{ORIGIN_PATH}.m_cellZ")),
            ],
            offset: [
                key(&format!("{ORIGIN_PATH}.m_vecX")),
                key(&format!("{ORIGIN_PATH}.m_vecY")),
                key(&format!("{ORIGIN_PATH}.m_vecZ")),
            ],
            team: key("m_iTeamNum"),
            controller: key("m_hController"),
        }
    }
}

/// Field keys on the `CCSPlayerController` serializer, resolved once.
struct CtrlKeys {
    steamid: Option<u64>,
    name: Option<u64>,
    money: Option<u64>,
}

impl CtrlKeys {
    fn resolve(ctx: &Context) -> Self {
        let ser = ctx.serializers.get(PLAYER_CONTROLLER_CLASS);
        let key = |name: &str| ser.and_then(|s| s.resolve_field_key(name));
        Self {
            steamid: key("m_steamID"),
            name: key("m_iszPlayerName"),
            money: key("m_pInGameMoneyServices.m_iAccount"),
        }
    }
}

/// Walk a pawn's `m_hMyWeapons` handles and fill the loadout fields of a
/// [`PlayerState`]: the primary / secondary weapon, per-type grenade counts,
/// and the full comma-separated inventory string (in slot order).
fn fill_loadout(
    ctx: &Context,
    pawn: &Entity,
    weapon_keys: &[Option<u64>],
    state: &mut PlayerState,
) {
    // Build the comma-joined inventory directly, without an intermediate Vec.
    let mut inventory = String::new();
    for &wkey in weapon_keys {
        let Some(weapon) = pawn
            .get_handle(wkey)
            .and_then(|h| ctx.entities.get_by_handle(h))
        else {
            continue;
        };
        let Some(info) = weapon_info(&weapon.class_name) else {
            continue;
        };
        if !inventory.is_empty() {
            inventory.push(',');
        }
        inventory.push_str(info.name);
        match info.slot {
            WeaponSlot::Primary => state.primary_weapon = Some(info.name),
            WeaponSlot::Secondary => state.secondary_weapon = Some(info.name),
            WeaponSlot::Grenade => match info.name {
                "hegrenade" => state.he_grenades += 1,
                "flashbang" => state.flashbangs += 1,
                "smokegrenade" => state.smoke_grenades += 1,
                "molotov" | "incendiary" => state.fire_grenades += 1,
                "decoy" => state.decoy_grenades += 1,
                _ => {}
            },
            WeaponSlot::C4 => state.has_bomb = true,
            WeaponSlot::Melee | WeaponSlot::Equipment => {}
        }
    }
    state.inventory = inventory;
}

/// Field keys read for every [`PlayerState`], resolved once per pass. Resolving
/// them per tick — especially the up-to-64 inventory-slot handles, each built
/// with `format!` — costs far more than reading them, and a snapshot pass reads
/// them on every tick.
struct SnapshotKeys {
    /// Numeric id of `CCSPlayerPawn`, so the per-entity class check is an integer
    /// compare rather than a `class_name` string compare (`-1` if absent).
    pawn_class: i32,
    pawn: PawnKeys,
    ctrl: CtrlKeys,
    health: Option<u64>,
    armor: Option<u64>,
    angles: Option<u64>,
    equip: Option<u64>,
    equip_round_start: Option<u64>,
    flags: Option<u64>,
    crouched: Option<u64>,
    walking: Option<u64>,
    scoped: Option<u64>,
    defusing: Option<u64>,
    flash: Option<u64>,
    in_bomb_zone: Option<u64>,
    has_helmet: Option<u64>,
    has_defuser: Option<u64>,
    active_weapon: Option<u64>,
    weapon_count: Option<u64>,
    weapons: Vec<Option<u64>>,
}

impl SnapshotKeys {
    fn resolve(ctx: &Context) -> Self {
        let ser = ctx.serializers.get(PLAYER_PAWN_CLASS);
        let key = |name: &str| ser.and_then(|s| s.resolve_field_key(name));
        SnapshotKeys {
            pawn_class: ctx.class_info.id_of(PLAYER_PAWN_CLASS).unwrap_or(-1),
            pawn: PawnKeys::resolve(ctx),
            ctrl: CtrlKeys::resolve(ctx),
            health: key("m_iHealth"),
            armor: key("m_ArmorValue"),
            angles: key("m_angEyeAngles"),
            equip: key("m_unCurrentEquipmentValue"),
            equip_round_start: key("m_unRoundStartEquipmentValue"),
            flags: key("m_fFlags"),
            crouched: key("m_pMovementServices.m_bDucked"),
            walking: key("m_bIsWalking"),
            scoped: key("m_bIsScoped"),
            defusing: key("m_bIsDefusing"),
            flash: key("m_flFlashDuration"),
            in_bomb_zone: key("m_bInBombZone"),
            has_helmet: key("m_pItemServices.m_bHasHelmet"),
            has_defuser: key("m_pItemServices.m_bHasDefuser"),
            active_weapon: key("m_pWeaponServices.m_hActiveWeapon"),
            // The loadout is a networked vector: its base field holds the live
            // element count, and each element is a handle at `...m_hMyWeapons.{i}`.
            weapon_count: key("m_pWeaponServices.m_hMyWeapons"),
            weapons: (0..MAX_INVENTORY)
                .map(|i| key(&format!("m_pWeaponServices.m_hMyWeapons.{i}")))
                .collect(),
        }
    }
}

/// The entity filter for a snapshot pass: player pawns and controllers, plus
/// every weapon class so held loadouts can be resolved from the filtered decode.
fn snapshot_filter() -> HashSet<&'static str> {
    let mut filter: HashSet<&'static str> =
        HashSet::from([PLAYER_PAWN_CLASS, PLAYER_CONTROLLER_CLASS]);
    filter.extend(weapon_classes());
    filter
}

/// Number of keyframe segments to decode a player-exact pass across: the CPU
/// count, overridable via `AWPY_TICK_SEGMENTS` (read fresh so a test can force
/// the serial path with `1`). `1` disables parallelism.
fn parallel_segment_budget() -> usize {
    std::env::var("AWPY_TICK_SEGMENTS")
        .ok()
        .and_then(|s| s.parse::<usize>().ok())
        .unwrap_or_else(|| {
            std::thread::available_parallelism()
                .map(|n| n.get())
                .unwrap_or(1)
        })
}

/// Split the demo into `n` contiguous `(start_offset, end_tick)` segments at
/// full-packet keyframes: segment 0 from the signon baseline, the rest
/// cold-restarting at an evenly-spaced full packet.
fn segment_ranges(offsets: &[(usize, i32)], n: usize) -> Vec<(Option<usize>, i32)> {
    (0..n)
        .map(|i| {
            let start = (i != 0).then(|| offsets[i * offsets.len() / n].0);
            let end_tick = if i == n - 1 {
                i32::MAX
            } else {
                offsets[(i + 1) * offsets.len() / n].1
            };
            (start, end_tick)
        })
        .collect()
}

/// Resolve a participant from the pawn `CHandle` carried in a game event.
///
/// Follows the handle to the pawn (for world position and side), then the
/// pawn's controller handle to the controller (for Steam id and name). Returns
/// an all-`None` [`ResolvedPlayer`] when the handle does not point at a live
/// player pawn.
fn resolve_player(ctx: &Context, pawn_handle: i64, pk: &PawnKeys, ck: &CtrlKeys) -> ResolvedPlayer {
    let Some(pawn) = ctx.entities.get_by_handle(pawn_handle as u32) else {
        return ResolvedPlayer::default();
    };
    if !pawn.class_name.contains("PlayerPawn") {
        return ResolvedPlayer::default();
    }
    resolve_from_pawn(ctx, pawn, pk, ck)
}

/// Resolve a participant from a player-pawn entity already in hand.
///
/// Reads side and world position off the pawn, then follows its controller
/// handle for the persistent Steam id and name. Use [`resolve_player`] when you
/// only have a pawn `CHandle` (e.g. from a game event).
fn resolve_from_pawn(ctx: &Context, pawn: &Entity, pk: &PawnKeys, ck: &CtrlKeys) -> ResolvedPlayer {
    let mut player = ResolvedPlayer {
        side: Some(team_name(pawn.get_i64(pk.team)).to_string()),
        ..Default::default()
    };

    // World position: cell index + in-cell offset per axis. Only reported when
    // the offset field is actually present on the pawn.
    if pk.offset[0].is_some_and(|k| pawn.fields.contains_key(&k)) {
        let coord =
            |i: usize| cell_to_world(pawn.get_i64(pk.cell[i]) as i32, pawn.get_f32(pk.offset[i]));
        player.x = Some(coord(0));
        player.y = Some(coord(1));
        player.z = Some(coord(2));
    }

    // Follow the controller handle for the persistent Steam id and name.
    if let Some(controller) = pawn
        .get_handle(pk.controller)
        .and_then(|h| ctx.entities.get_by_handle(h))
    {
        player.steamid = controller.get_u64(ck.steamid);
        player.name = controller.get_string(ck.name);
    }

    player
}

/// Field keys on the `CCSGameRulesProxy` serializer, resolved once.
struct GameRulesKeys {
    warmup: Option<u64>,
    freeze: Option<u64>,
    total_rounds: Option<u64>,
    win_status: Option<u64>,
    win_reason: Option<u64>,
}

impl GameRulesKeys {
    fn resolve(ser: &crate::entity::Serializer) -> Self {
        let key = |name: &str| ser.resolve_field_key(name);
        Self {
            warmup: key("m_pGameRules.m_bWarmupPeriod"),
            freeze: key("m_pGameRules.m_bFreezePeriod"),
            total_rounds: key("m_pGameRules.m_totalRoundsPlayed"),
            win_status: key("m_pGameRules.m_iRoundWinStatus"),
            win_reason: key("m_pGameRules.m_eRoundWinReason"),
        }
    }
}

/// The four player-enriched, event-based datasets ([`Parser::kills`],
/// [`Parser::damages`], [`Parser::bomb`], [`Parser::blinds`]), built together in
/// one entity-decode pass by [`Parser::event_datasets`].
pub struct EventDatasets {
    pub kills: Vec<Kill>,
    pub damages: Vec<Damage>,
    pub bomb: Vec<BombEvent>,
    pub blinds: Vec<Blind>,
    pub shots: Vec<Shot>,
}

/// A flashbang detonation: the thrower's pawn handle and the blast site, used
/// to attribute a [`Blind`] to its thrower.
struct Detonation {
    thrower_pawn: i64,
    x: Option<f32>,
    y: Option<f32>,
    z: Option<f32>,
}

/// Squared distance from a detonation to a point; a detonation missing
/// coordinates sorts last.
fn det_dist2(d: &Detonation, x: f32, y: f32, z: f32) -> f32 {
    match (d.x, d.y, d.z) {
        (Some(dx), Some(dy), Some(dz)) => (dx - x).powi(2) + (dy - y).powi(2) + (dz - z).powi(2),
        _ => f32::INFINITY,
    }
}

/// Group row indices by the tick their event fired on, so the decode can fill
/// the right rows when it reaches each tick.
fn index_by_tick(ticks: impl Iterator<Item = i32>) -> HashMap<i32, Vec<usize>> {
    let mut by_tick: HashMap<i32, Vec<usize>> = HashMap::new();
    for (i, tick) in ticks.enumerate() {
        by_tick.entry(tick).or_default().push(i);
    }
    by_tick
}

/// Fill a [`Kill`] row from the player-death event and entity state at its tick.
fn fill_kill(kill: &mut Kill, e: &GameEvent, ctx: &Context, pk: &PawnKeys, ck: &CtrlKeys) {
    let k = Keys(&e.keys);
    // The `*_pawn` keys are CHandles to each participant's pawn; a `65535` user
    // id means "no participant" (e.g. no assister).
    let attacker = resolve_player(ctx, k.i64("attacker_pawn"), pk, ck);
    let victim = resolve_player(ctx, k.i64("userid_pawn"), pk, ck);
    let assister = if k.i32("assister") == NO_USER_ID {
        ResolvedPlayer::default()
    } else {
        resolve_player(ctx, k.i64("assister_pawn"), pk, ck)
    };
    attacker.assign_to(
        &mut kill.attacker_steamid,
        &mut kill.attacker_name,
        &mut kill.attacker_side,
        &mut kill.attacker_x,
        &mut kill.attacker_y,
        &mut kill.attacker_z,
    );
    victim.assign_to(
        &mut kill.victim_steamid,
        &mut kill.victim_name,
        &mut kill.victim_side,
        &mut kill.victim_x,
        &mut kill.victim_y,
        &mut kill.victim_z,
    );
    assister.assign_to(
        &mut kill.assister_steamid,
        &mut kill.assister_name,
        &mut kill.assister_side,
        &mut kill.assister_x,
        &mut kill.assister_y,
        &mut kill.assister_z,
    );
}

/// Fill a [`Damage`] row from the player-hurt event and entity state.
fn fill_damage(dmg: &mut Damage, e: &GameEvent, ctx: &Context, pk: &PawnKeys, ck: &CtrlKeys) {
    let k = Keys(&e.keys);
    let attacker = resolve_player(ctx, k.i64("attacker_pawn"), pk, ck);
    let victim = resolve_player(ctx, k.i64("userid_pawn"), pk, ck);
    attacker.assign_to(
        &mut dmg.attacker_steamid,
        &mut dmg.attacker_name,
        &mut dmg.attacker_side,
        &mut dmg.attacker_x,
        &mut dmg.attacker_y,
        &mut dmg.attacker_z,
    );
    victim.assign_to(
        &mut dmg.victim_steamid,
        &mut dmg.victim_name,
        &mut dmg.victim_side,
        &mut dmg.victim_x,
        &mut dmg.victim_y,
        &mut dmg.victim_z,
    );
}

/// The active planted-C4's bomb site (0 = A, 1 = B), or `None` when no bomb is
/// currently planted.
fn bomb_site(ctx: &Context, site_key: Option<u64>) -> Option<&'static str> {
    ctx.entities
        .iter()
        .find(|(_, e)| e.class_name == PLANTED_C4_CLASS)
        .filter(|(_, e)| site_key.is_some_and(|k| e.fields.contains_key(&k)))
        .and_then(|(_, e)| match e.get_i64(site_key) {
            0 => Some("A"),
            1 => Some("B"),
            _ => None,
        })
}

/// Fill a [`BombEvent`] row from the bomb event, the acting player, and the
/// (already-resolved) bomb site.
fn fill_bomb(
    row: &mut BombEvent,
    e: &GameEvent,
    ctx: &Context,
    pk: &PawnKeys,
    ck: &CtrlKeys,
    bombsite: Option<&str>,
) {
    let k = Keys(&e.keys);
    let player = resolve_player(ctx, k.i64("userid_pawn"), pk, ck);
    row.steamid = player.steamid;
    row.name = player.name;
    row.x = player.x;
    row.y = player.y;
    row.z = player.z;
    row.bombsite = bombsite.map(String::from);
}

/// Pawn field keys read for every [`Shot`], resolved once per pass: the shooter's
/// view angles, scoped flag, and active-weapon handle.
struct ShotKeys {
    angles: Option<u64>,
    scoped: Option<u64>,
    weapon_handle: Option<u64>,
}

impl ShotKeys {
    fn resolve(ctx: &Context) -> Self {
        let ser = ctx.serializers.get(PLAYER_PAWN_CLASS);
        let key = |name: &str| ser.and_then(|s| s.resolve_field_key(name));
        Self {
            angles: key("m_angEyeAngles"),
            scoped: key("m_bIsScoped"),
            weapon_handle: key("m_pWeaponServices.m_hActiveWeapon"),
        }
    }
}

/// Fill a [`Shot`] row from the `weapon_fire` event and entity state: the
/// shooter (resolved from the pawn handle), the pawn's angles/scoped flag, and
/// the active weapon's clip and accuracy penalty (followed through the weapon
/// handle). `weapon_keys` caches each weapon class's clip/accuracy field keys
/// across ticks.
fn fill_shot(
    shot: &mut Shot,
    e: &GameEvent,
    ctx: &Context,
    pk: &PawnKeys,
    ck: &CtrlKeys,
    sk: &ShotKeys,
    weapon_keys: &mut HashMap<String, (Option<u64>, Option<u64>)>,
) {
    let k = Keys(&e.keys);
    let player = resolve_player(ctx, k.i64("userid_pawn"), pk, ck);
    shot.steamid = player.steamid;
    shot.name = player.name;
    shot.side = player.side;
    shot.x = player.x;
    shot.y = player.y;
    shot.z = player.z;

    let Some(pawn) = ctx.entities.get_by_handle(k.i64("userid_pawn") as u32) else {
        return;
    };
    let angles = pawn.get_qangle(sk.angles);
    shot.pitch = Some(angles[0]);
    shot.yaw = Some(angles[1]);
    shot.scoped = Some(pawn.get_bool(sk.scoped));

    // Follow the active-weapon handle to the weapon entity for clip / accuracy.
    if let Some(weapon) = pawn
        .get_handle(sk.weapon_handle)
        .and_then(|h| ctx.entities.get_by_handle(h))
        && let Some(wser) = ctx.serializers.get(&weapon.class_name)
    {
        let (clip_k, acc_k) = *weapon_keys
            .entry(weapon.class_name.clone())
            .or_insert_with(|| {
                (
                    wser.resolve_field_key("m_iClip1"),
                    wser.resolve_field_key("m_fAccuracyPenalty"),
                )
            });
        shot.num_bullets_remaining = Some(weapon.get_i64(clip_k) as i32);
        shot.inaccuracy = Some(weapon.get_f32(acc_k));
    }
}

/// Detect new blinds on this tick: a rising edge of each player pawn's flash
/// duration, attributed to a detonation on the same tick. `prev_flash` carries
/// the previous tick's duration per pawn index across calls.
fn detect_blinds(
    ctx: &Context,
    detonations: &HashMap<i32, Vec<Detonation>>,
    prev_flash: &mut HashMap<i32, f32>,
    flash_key: Option<u64>,
    pk: &PawnKeys,
    ck: &CtrlKeys,
    out: &mut Vec<Blind>,
) {
    let dets = detonations.get(&ctx.tick);
    for (idx, pawn) in ctx.entities.iter() {
        if !pawn.active || pawn.class_name != PLAYER_PAWN_CLASS {
            continue;
        }
        let cur = pawn.get_f32(flash_key);
        let prev = prev_flash.insert(idx, cur).unwrap_or(0.0);
        // A new blind is a rising edge above the noise floor. Requiring a
        // detonation on this tick both supplies the thrower and rejects spurious
        // edges (e.g. from recycled entity indices).
        if cur <= FLASH_MIN_DURATION || cur <= prev + FLASH_EDGE_MARGIN {
            continue;
        }
        let Some(dets) = dets else {
            continue;
        };
        let victim = resolve_from_pawn(ctx, pawn, pk, ck);
        // Attribute to the nearest detonation (by victim position); with a single
        // detonation this is unambiguous.
        let det = match (victim.x, victim.y, victim.z) {
            (Some(vx), Some(vy), Some(vz)) if dets.len() > 1 => dets
                .iter()
                .min_by(|a, b| det_dist2(a, vx, vy, vz).total_cmp(&det_dist2(b, vx, vy, vz)))
                .expect("dets is non-empty"),
            _ => &dets[0],
        };
        let attacker = resolve_player(ctx, det.thrower_pawn, pk, ck);
        let mut blind = Blind {
            tick: ctx.tick,
            duration: cur,
            ..Default::default()
        };
        attacker.assign_to(
            &mut blind.attacker_steamid,
            &mut blind.attacker_name,
            &mut blind.attacker_side,
            &mut blind.attacker_x,
            &mut blind.attacker_y,
            &mut blind.attacker_z,
        );
        victim.assign_to(
            &mut blind.victim_steamid,
            &mut blind.victim_name,
            &mut blind.victim_side,
            &mut blind.victim_x,
            &mut blind.victim_y,
            &mut blind.victim_z,
        );
        out.push(blind);
    }
}

impl Parser {
    /// Reconstruct per-round information from `CCSGameRules` entity state.
    ///
    /// Rounds are delimited by transitions of the game-rules entity rather than
    /// game events, so this works even on demos that omit `round_start` /
    /// `round_end` events. A round is emitted each time `m_totalRoundsPlayed`
    /// increments (the canonical "a round was completed" signal — including the
    /// match-deciding round, which coincides with `game_over`); the winner and
    /// reason are read from `m_iRoundWinStatus` / `m_eRoundWinReason` at that
    /// tick, and `start_tick` / `freeze_end_tick` from the surrounding
    /// `m_bFreezePeriod` transitions. Warmup freeze periods are ignored.
    ///
    /// This performs a full entity decode (filtered to the game-rules entity),
    /// so it is slower than [`Parser::events`].
    pub fn rounds(&self) -> Result<Vec<Round>> {
        let filter: HashSet<&str> = HashSet::from([GAME_RULES_CLASS]);

        let mut rounds: Vec<Round> = Vec::new();
        let mut start_tick: Option<i32> = None;
        let mut freeze_end_tick: Option<i32> = None;
        let mut prev_freeze = false;
        let mut prev_total: i32 = 0;
        let mut keys: Option<GameRulesKeys> = None;

        self.run_to_end_filtered(&filter, |ctx| {
            let Some((_, entity)) = ctx
                .entities
                .iter()
                .find(|(_, e)| e.class_name == GAME_RULES_CLASS)
            else {
                return;
            };
            let Some(ser) = ctx.serializers.get(GAME_RULES_CLASS) else {
                return;
            };
            let k = keys.get_or_insert_with(|| GameRulesKeys::resolve(ser));

            let warmup = entity.get_bool(k.warmup);
            let freeze = entity.get_bool(k.freeze);
            let total = entity.get_i64(k.total_rounds) as i32;

            // A match restart (`mp_restartgame`, fired when the real match begins
            // — typically right after a knife round) resets the round counter.
            // Everything emitted so far therefore belongs to the pre-match
            // period: the knife round and any warmup skirmishing. Discard it and
            // begin the match here.
            //
            // Without this, a knife round that ticked the counter 0 -> 1 survives
            // as a round numbered 1, the real first round is emitted as a *second*
            // round 1, and — because the discarded round starts at tick 0 —
            // `round_of` in `stats` buckets every pre-match kill into it, inflating
            // player stats and the round count that ADR / KAST divide by.
            if total < prev_total {
                rounds.clear();
                start_tick = None;
                freeze_end_tick = None;
            }

            // Emit the completed round FIRST, before handling this tick's freeze
            // transition. A round completes exactly when the round counter ticks
            // up by one. (`== prev + 1` rather than `>` so a mid-join demo whose
            // first observed count is already high doesn't fabricate a round.)
            // The match-deciding round flips the freeze period back on for the
            // "game over" screen on the very same tick, so emitting first keeps
            // that round's real start / freeze-end ticks instead of clobbering
            // them with the post-match freeze.
            //
            // Warmup never produces a scored round, so a counter tick there is
            // an artifact and is ignored.
            if !warmup && total == prev_total + 1 {
                let win_status = entity.get_i64(k.win_status);
                let reason = entity.get_i64(k.win_reason) as i32;
                rounds.push(Round {
                    round_num: total,
                    start_tick,
                    freeze_end_tick,
                    end_tick: ctx.tick,
                    official_end_tick: None,
                    winner: win_status as i32,
                    winner_side: team_name(win_status).to_string(),
                    reason,
                    reason_name: round_end_reason_name(reason as i64).to_string(),
                    is_knife_round: false, // filled in by mark_knife_rounds below
                });
                start_tick = None;
                freeze_end_tick = None;
            }

            // Track freeze-period transitions (post-warmup) for the next round's
            // start / freeze-end ticks.
            if !warmup {
                if freeze && !prev_freeze {
                    // The next round's freeze beginning marks the previous
                    // round's official end (the post-round reset).
                    if let Some(last) = rounds.last_mut()
                        && last.official_end_tick.is_none()
                    {
                        last.official_end_tick = Some(ctx.tick);
                    }
                    start_tick = Some(ctx.tick);
                    freeze_end_tick = None;
                } else if !freeze && prev_freeze {
                    freeze_end_tick = Some(ctx.tick);
                }
            }

            prev_freeze = freeze;
            prev_total = total;
        })?;

        self.mark_knife_rounds(&mut rounds)?;
        Ok(rounds)
    }

    /// Flag knife rounds in place: a round with at least one kill whose kills are
    /// all melee (knife / bayonet) and none from a firearm or grenade. Uses only
    /// the (cheap) `player_death` event stream — no entity decode.
    fn mark_knife_rounds(&self, rounds: &mut [Round]) -> Result<()> {
        if rounds.is_empty() {
            return Ok(());
        }
        // Round start ticks, ascending, for bucketing deaths; anything before
        // the first round's start is warmup and ignored.
        let starts: Vec<i32> = rounds
            .iter()
            .map(|r| r.start_tick.or(r.freeze_end_tick).unwrap_or(r.end_tick))
            .collect();
        // Per round: (knife kills, firearm/grenade kills).
        let mut tally = vec![(0u32, 0u32); rounds.len()];
        for e in self.events_ref()? {
            if e.name != "player_death" || e.tick < starts[0] {
                continue;
            }
            let idx = starts.partition_point(|&s| s <= e.tick) - 1;
            let weapon = Keys(&e.keys).string("weapon");
            if weapon.contains("knife") || weapon.contains("bayonet") {
                tally[idx].0 += 1;
            } else if weapon != "world" && !weapon.is_empty() {
                tally[idx].1 += 1;
            }
        }
        for (r, (knife, firearm)) in rounds.iter_mut().zip(tally) {
            r.is_knife_round = knife > 0 && firearm == 0;
        }
        Ok(())
    }

    /// Build [`kills`](Self::kills), [`damages`](Self::damages),
    /// [`bomb`](Self::bomb), [`blinds`](Self::blinds) and [`shots`](Self::shots)
    /// in a **single** entity decode pass instead of one pass each.
    ///
    /// All five enrich player pawn / controller state (bomb additionally reads
    /// the planted C4; shots additionally follows the active-weapon handle to a
    /// weapon entity), so a single `run_to_end_filtered` over the union of their
    /// classes — dispatched per tick to the datasets with an event on that tick,
    /// plus the per-tick flash-edge scan blinds needs — yields all five for
    /// roughly the cost of one. Adding the weapon classes for `shots` also makes
    /// `shots` itself far cheaper than its old *unfiltered* pass, which decoded
    /// every entity in the demo.
    pub fn event_datasets(&self) -> Result<EventDatasets> {
        let events = self.events_ref()?;

        // A row per matching event, plus a tick -> row-indices map so the decode
        // knows which rows to fill when it reaches a tick.
        let kill_raw: Vec<&GameEvent> =
            events.iter().filter(|e| e.name == "player_death").collect();
        let mut kills: Vec<Kill> = kill_raw.iter().map(|e| kill_event_fields(e)).collect();
        let kill_by_tick = index_by_tick(kill_raw.iter().map(|e| e.tick));

        let hurt_raw: Vec<&GameEvent> = events.iter().filter(|e| e.name == "player_hurt").collect();
        let mut damages: Vec<Damage> = hurt_raw.iter().map(|e| damage_event_fields(e)).collect();
        let hurt_by_tick = index_by_tick(hurt_raw.iter().map(|e| e.tick));

        let bomb_raw: Vec<(&str, &GameEvent)> = events
            .iter()
            .filter_map(|e| {
                BOMB_EVENTS
                    .iter()
                    .find(|(name, _)| *name == e.name)
                    .map(|(_, label)| (*label, e))
            })
            .collect();
        let mut bomb: Vec<BombEvent> = bomb_raw
            .iter()
            .map(|(label, e)| BombEvent {
                tick: e.tick,
                event: label.to_string(),
                ..Default::default()
            })
            .collect();
        let bomb_by_tick = index_by_tick(bomb_raw.iter().map(|(_, e)| e.tick));

        // Flashbang detonations grouped by tick, for blind attribution.
        let mut detonations: HashMap<i32, Vec<Detonation>> = HashMap::new();
        for e in events {
            if e.name == "flashbang_detonate" {
                let k = Keys(&e.keys);
                detonations.entry(e.tick).or_default().push(Detonation {
                    thrower_pawn: k.i64("userid_pawn"),
                    x: k.f32("x"),
                    y: k.f32("y"),
                    z: k.f32("z"),
                });
            }
        }

        let shot_raw: Vec<&GameEvent> = events.iter().filter(|e| e.name == "weapon_fire").collect();
        let mut shots: Vec<Shot> = shot_raw
            .iter()
            .map(|e| Shot {
                tick: e.tick,
                weapon: Keys(&e.keys).string("weapon"),
                ..Default::default()
            })
            .collect();
        let shot_by_tick = index_by_tick(shot_raw.iter().map(|e| e.tick));

        // Shots follow the active-weapon handle to a weapon entity, so the pass
        // must also decode weapon entities — see [`weapon_classes`].
        let mut filter: HashSet<&str> =
            HashSet::from([PLAYER_PAWN_CLASS, PLAYER_CONTROLLER_CLASS, PLANTED_C4_CLASS]);
        filter.extend(weapon_classes());
        let mut pawn_keys: Option<PawnKeys> = None;
        let mut ctrl_keys: Option<CtrlKeys> = None;
        let mut site_key: Option<Option<u64>> = None;
        let mut flash_key: Option<Option<u64>> = None;
        let mut prev_flash: HashMap<i32, f32> = HashMap::new();
        let mut blinds: Vec<Blind> = Vec::new();
        let mut shot_keys: Option<ShotKeys> = None;
        let mut weapon_keys: HashMap<String, (Option<u64>, Option<u64>)> = HashMap::new();

        self.run_to_end_filtered(&filter, |ctx| {
            let pk = pawn_keys.get_or_insert_with(|| PawnKeys::resolve(ctx));
            let ck = ctrl_keys.get_or_insert_with(|| CtrlKeys::resolve(ctx));

            if let Some(indices) = kill_by_tick.get(&ctx.tick) {
                for &i in indices {
                    fill_kill(&mut kills[i], kill_raw[i], ctx, pk, ck);
                }
            }
            if let Some(indices) = hurt_by_tick.get(&ctx.tick) {
                for &i in indices {
                    fill_damage(&mut damages[i], hurt_raw[i], ctx, pk, ck);
                }
            }
            if let Some(indices) = bomb_by_tick.get(&ctx.tick) {
                let sk = *site_key.get_or_insert_with(|| {
                    ctx.serializers
                        .get(PLANTED_C4_CLASS)
                        .and_then(|s| s.resolve_field_key("m_nBombSite"))
                });
                let site = bomb_site(ctx, sk);
                for &i in indices {
                    fill_bomb(&mut bomb[i], bomb_raw[i].1, ctx, pk, ck, site);
                }
            }
            if let Some(indices) = shot_by_tick.get(&ctx.tick) {
                let shk = shot_keys.get_or_insert_with(|| ShotKeys::resolve(ctx));
                for &i in indices {
                    fill_shot(
                        &mut shots[i],
                        shot_raw[i],
                        ctx,
                        pk,
                        ck,
                        shk,
                        &mut weapon_keys,
                    );
                }
            }

            // Blinds are found from a per-tick rising edge, so this runs every tick.
            let fk = *flash_key.get_or_insert_with(|| {
                ctx.serializers
                    .get(PLAYER_PAWN_CLASS)
                    .and_then(|s| s.resolve_field_key("m_flFlashDuration"))
            });
            detect_blinds(ctx, &detonations, &mut prev_flash, fk, pk, ck, &mut blinds);
        })?;

        // Trades need every kill's resolved sides, so they are classified after
        // the decode has filled the participants in.
        let trade_ticks = (TRADE_SECONDS * self.tickrate()).round() as i32;
        let flags = trade_flags(&kills, trade_ticks);
        for (kill, (is_trade, victim_traded)) in kills.iter_mut().zip(flags) {
            kill.is_trade = is_trade;
            kill.victim_traded = victim_traded;
        }

        Ok(EventDatasets {
            kills,
            damages,
            bomb,
            blinds,
            shots,
        })
    }

    /// Collect every kill (`player_death` game event), enriched with each
    /// participant's Steam id, name, side, and world position at the kill tick.
    ///
    /// The `player_death` events resolve their own names and carry the
    /// participants' pawn handles; a filtered decode of the player pawn and
    /// controller entities then resolves the attacker / victim / assister by
    /// following each pawn handle to the pawn (position, side) and on to its
    /// controller (Steam id, name). Slower than a raw event scan.
    pub fn kills(&self) -> Result<Vec<Kill>> {
        Ok(self.event_datasets()?.kills)
    }

    /// Collect every damage instance (`player_hurt` game event), enriched with
    /// the resolved attacker and victim and the victim's health/armor before and
    /// after the hit. Like [`Parser::kills`], this performs an entity decode.
    ///
    /// Built alongside kills / bomb / blinds in [`Parser::event_datasets`].
    pub fn damages(&self) -> Result<Vec<Damage>> {
        Ok(self.event_datasets()?.damages)
    }

    /// Collect bomb actions (pickup / drop / plant / defuse) with the acting
    /// player (Steam id, name, world position) and, while planted, the bomb
    /// site. Note that some demos don't emit the begin/abort-plant events, so
    /// `start_plant` / `interrupt_plant` rows may be absent.
    ///
    /// Built alongside kills / damages / blinds in [`Parser::event_datasets`].
    pub fn bomb(&self) -> Result<Vec<BombEvent>> {
        Ok(self.event_datasets()?.bomb)
    }

    /// Pair `start_event` / `end_event` game events (by their `entityid` key,
    /// in tick order) into active `[start_tick, end_tick]` intervals per entity
    /// index. Used to bound fires / smokes to the game's own burn / smoke window
    /// rather than the (longer) entity lifetime.
    fn burn_intervals(
        &self,
        start_event: &str,
        end_event: &str,
    ) -> Result<HashMap<i32, Vec<(i32, i32)>>> {
        let events = self.events_ref()?;
        let mut open: HashMap<i32, i32> = HashMap::new();
        let mut intervals: HashMap<i32, Vec<(i32, i32)>> = HashMap::new();
        for e in events {
            if e.name == start_event {
                open.insert(Keys(&e.keys).i32("entityid"), e.tick);
            } else if e.name == end_event {
                let id = Keys(&e.keys).i32("entityid");
                if let Some(start) = open.remove(&id) {
                    intervals.entry(id).or_default().push((start, e.tick));
                }
            }
        }
        Ok(intervals)
    }

    /// Track projectile entities tick by tick in one pass, sampling each active
    /// entity's world position and resolved thrower.
    ///
    /// `modes` maps each tracked class to one or more `(destination, sampling)`
    /// pairs — a `CSmokeGrenadeProjectile` feeds both the grenade dataset (its
    /// throw, as a trajectory) and the smoke dataset (its cloud, windowed). Rows
    /// come back interleaved, each tagged with its [`ProjKind`]; the caller
    /// splits by tag. Trajectory rows carry a placeholder `end_tick` of `0` —
    /// fill it with [`fill_trajectory_ends`].
    fn track_projectiles(
        &self,
        modes: &HashMap<&str, Vec<(ProjKind, ProjMode)>>,
    ) -> Result<Vec<(ProjKind, TrackedRow)>> {
        let mut filter: HashSet<&str> = modes.keys().copied().collect();
        filter.insert(PLAYER_PAWN_CLASS);
        filter.insert(PLAYER_CONTROLLER_CLASS);

        let mut rows: Vec<(ProjKind, TrackedRow)> = Vec::new();
        let mut pawn_keys: Option<PawnKeys> = None;
        let mut ctrl_keys: Option<CtrlKeys> = None;
        let mut pos_keys: HashMap<String, PositionKeys> = HashMap::new();
        // (m_hThrower key, m_hOwnerEntity key) per class.
        let mut thrower_keys: HashMap<String, (Option<u64>, Option<u64>)> = HashMap::new();
        // Trajectory bookkeeping (grenades only): indices seen last tick, each
        // live instance's start tick, and its last position.
        let mut prev: HashSet<i32> = HashSet::new();
        let mut starts: HashMap<i32, i32> = HashMap::new();
        let mut last_pos: HashMap<i32, (f32, f32, f32)> = HashMap::new();

        self.run_to_end_filtered(&filter, |ctx| {
            let pk = pawn_keys.get_or_insert_with(|| PawnKeys::resolve(ctx));
            let ck = ctrl_keys.get_or_insert_with(|| CtrlKeys::resolve(ctx));
            let mut current: HashSet<i32> = HashSet::new();

            for (_, e) in ctx.entities.iter() {
                if !e.active {
                    continue;
                }
                let Some(trackers) = modes.get(e.class_name.as_str()) else {
                    continue;
                };
                let Some(ser) = ctx.serializers.get(&e.class_name) else {
                    continue;
                };
                let posk = pos_keys
                    .entry(e.class_name.clone())
                    .or_insert_with(|| PositionKeys::resolve(ser));
                let Some((x, y, z)) = posk.world(e) else {
                    continue;
                };

                // Grenade projectiles carry `m_hThrower`; infernos instead carry
                // `m_hOwnerEntity`. Resolve whichever points at a player pawn
                // (once per entity — every tracker on it shares the thrower).
                let (tk, ok) = *thrower_keys.entry(e.class_name.clone()).or_insert_with(|| {
                    (
                        ser.resolve_field_key("m_hThrower"),
                        ser.resolve_field_key("m_hOwnerEntity"),
                    )
                });
                let thrower = e
                    .get_handle(tk)
                    .or_else(|| e.get_handle(ok))
                    .map(|h| resolve_player(ctx, h as i64, pk, ck))
                    .unwrap_or_default();

                for (kind, mode) in trackers {
                    // Windowed classes only emit inside an active window;
                    // trajectories derive the start from entity presence and skip
                    // ticks with no movement. Only trajectories touch prev /
                    // starts / last_pos, matching the per-class passes this
                    // replaced.
                    let (start_tick, end_tick) = match mode {
                        ProjMode::Windowed(w) => {
                            let Some(&(s, en)) = w.get(&e.index).and_then(|v| {
                                v.iter().find(|(s, en)| (*s..=*en).contains(&ctx.tick))
                            }) else {
                                continue;
                            };
                            (s, en)
                        }
                        ProjMode::Trajectory => {
                            current.insert(e.index);
                            if !prev.contains(&e.index) {
                                starts.insert(e.index, ctx.tick);
                            }
                            let start = *starts.get(&e.index).unwrap_or(&ctx.tick);
                            if last_pos.get(&e.index) == Some(&(x, y, z)) {
                                continue;
                            }
                            last_pos.insert(e.index, (x, y, z));
                            (start, 0)
                        }
                    };

                    rows.push((
                        *kind,
                        TrackedRow {
                            tick: ctx.tick,
                            entity_id: e.index,
                            class_name: e.class_name.clone(),
                            x,
                            y,
                            z,
                            thrower: thrower.clone(),
                            start_tick,
                            end_tick,
                        },
                    ));
                }
            }
            prev = current;
        })?;

        Ok(rows)
    }

    /// Build the three projectile datasets — [`grenades`](Self::grenades),
    /// [`fires`](Self::fires), [`smokes`](Self::smokes) — in a **single** entity
    /// decode pass instead of one each.
    ///
    /// They all track projectile entities against player pawn / controller
    /// state, so one `track_projectiles` pass over
    /// the union of their classes yields all three. The rows are split by class
    /// and finished per dataset (trajectory end-fill for grenades; instance
    /// collapse for fires / smokes).
    pub fn projectiles(&self) -> Result<Projectiles> {
        let fire_windows = self.burn_intervals("inferno_startburn", "inferno_expire")?;
        let smoke_windows = self.burn_intervals("smokegrenade_detonate", "smokegrenade_expired")?;

        // Every grenade projectile class is a grenade trajectory; CInferno is a
        // fire; CSmokeGrenadeProjectile is *also* a smoke (its cloud), so that
        // class carries two trackers.
        let mut modes: HashMap<&str, Vec<(ProjKind, ProjMode)>> = grenade_projectile_classes()
            .map(|class| (class, vec![(ProjKind::Grenade, ProjMode::Trajectory)]))
            .collect();
        modes
            .entry(INFERNO_CLASS)
            .or_default()
            .push((ProjKind::Fire, ProjMode::Windowed(&fire_windows)));
        modes
            .entry(SMOKE_CLASS)
            .or_default()
            .push((ProjKind::Smoke, ProjMode::Windowed(&smoke_windows)));

        let mut grenade_rows = Vec::new();
        let mut fire_rows = Vec::new();
        let mut smoke_rows = Vec::new();
        for (kind, row) in self.track_projectiles(&modes)? {
            match kind {
                ProjKind::Grenade => grenade_rows.push(row),
                ProjKind::Fire => fire_rows.push(row),
                ProjKind::Smoke => smoke_rows.push(row),
            }
        }
        fill_trajectory_ends(&mut grenade_rows);

        let grenades = grenade_rows
            .into_iter()
            .map(|r| Grenade {
                tick: r.tick,
                thrower_name: r.thrower.name,
                thrower_steamid: r.thrower.steamid,
                thrower_side: r.thrower.side,
                grenade_type: grenade_type(&r.class_name).unwrap_or("grenade").to_string(),
                entity_id: r.entity_id,
                x: r.x,
                y: r.y,
                z: r.z,
            })
            .collect();
        let fires = collapse_instances(fire_rows)
            .into_iter()
            .map(|r| Fire {
                start_tick: r.start_tick,
                end_tick: r.end_tick,
                thrower_name: r.thrower.name,
                thrower_steamid: r.thrower.steamid,
                thrower_side: r.thrower.side,
                fire_type: "inferno".to_string(),
                entity_id: r.entity_id,
                x: r.x,
                y: r.y,
                z: r.z,
            })
            .collect();
        let smokes = collapse_instances(smoke_rows)
            .into_iter()
            .map(|r| Smoke {
                start_tick: r.start_tick,
                end_tick: r.end_tick,
                thrower_name: r.thrower.name,
                thrower_steamid: r.thrower.steamid,
                thrower_side: r.thrower.side,
                entity_id: r.entity_id,
                x: r.x,
                y: r.y,
                z: r.z,
            })
            .collect();

        Ok(Projectiles {
            grenades,
            fires,
            smokes,
        })
    }

    /// Trajectories of thrown grenades: one row per tick each grenade projectile
    /// is live, with its position and resolved thrower.
    ///
    /// Built alongside fires / smokes in [`Parser::projectiles`].
    pub fn grenades(&self) -> Result<Vec<Grenade>> {
        Ok(self.projectiles()?.grenades)
    }

    /// Burning infernos (molotov / incendiary): one row per fire, with its
    /// landing position, thrower, and burn window `[start_tick, end_tick]`. The
    /// window comes from the `inferno_startburn` / `inferno_expire` events (the
    /// ~7 s fire), not the longer entity lifetime.
    ///
    /// Built alongside grenades / smokes in [`Parser::projectiles`].
    pub fn fires(&self) -> Result<Vec<Fire>> {
        Ok(self.projectiles()?.fires)
    }

    /// Deployed smoke clouds: one row per smoke, with its position, thrower, and
    /// active window `[start_tick, end_tick]`. The window comes from the
    /// `smokegrenade_detonate` / `smokegrenade_expired` events (the deployed
    /// cloud), so the pre-detonation throw is excluded.
    ///
    /// Built alongside grenades / fires in [`Parser::projectiles`].
    pub fn smokes(&self) -> Result<Vec<Smoke>> {
        Ok(self.projectiles()?.smokes)
    }

    /// Every shot fired (`weapon_fire` game event), enriched with the shooter's
    /// Steam id, name, side, position, and view angles, plus the active weapon's
    /// scoped state, accuracy penalty, and remaining clip.
    ///
    /// Built alongside kills / damages / bomb / blinds in
    /// [`Parser::event_datasets`] — reading the active weapon requires decoding
    /// weapon entities, which the shared pass now includes.
    pub fn shots(&self) -> Result<Vec<Shot>> {
        Ok(self.event_datasets()?.shots)
    }
}

/// A player seen in the demo, from `CCSPlayerController` state.
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct Player {
    /// Steam id (0 for bots).
    pub steamid: Option<u64>,
    pub name: Option<String>,
    /// Last observed side (players swap at halftime).
    pub side: Option<String>,
    /// The organization the player's team was playing under when they were last
    /// observed (`CCSTeam::m_szClanTeamname`, e.g. `"Imperial"`).
    ///
    /// Set by tournament servers and by anything that names its teams; empty in
    /// casual matchmaking, where it is `None`. Because it is captured alongside
    /// [`side`](Self::side) rather than at the end of the demo, a player who
    /// leaves mid-match keeps the clan they actually played for, not whoever
    /// held their side afterwards.
    pub team_clan_name: Option<String>,
}

/// One player's state at a tick (see [`Parser::snapshot`]).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct PlayerState {
    pub tick: i32,
    pub steamid: Option<u64>,
    pub name: Option<String>,
    /// `"terrorist"` / `"counter-terrorist"` — a static string, so borrowed (no
    /// per-tick allocation).
    pub side: Option<&'static str>,
    pub x: Option<f32>,
    pub y: Option<f32>,
    pub z: Option<f32>,
    pub pitch: f32,
    pub yaw: f32,
    pub health: i32,
    pub armor: i32,
    /// Whether the player has kevlar + helmet.
    pub has_helmet: bool,
    /// Whether the player has a defuse kit.
    pub has_defuser: bool,
    /// Whether the player is carrying the bomb (a `CC4` in their loadout).
    pub has_bomb: bool,
    // ── Weapons ──
    /// Short name of the weapon the player is actively holding, if any (follows
    /// `m_hActiveWeapon`). A static weapon name, so borrowed. (Per-shot clip and
    /// accuracy live on [`Parser::shots`], which reads the weapon's own state.)
    pub active_weapon: Option<&'static str>,
    /// Short name of the primary-slot weapon (rifle / SMG / shotgun / sniper /
    /// LMG) held, if any. A static weapon name, so borrowed (no allocation).
    pub primary_weapon: Option<&'static str>,
    /// Short name of the secondary-slot weapon (pistol) held, if any.
    pub secondary_weapon: Option<&'static str>,
    /// Number of fire grenades held (molotov and incendiary combined).
    pub fire_grenades: i32,
    /// Number of smoke grenades held.
    pub smoke_grenades: i32,
    /// Number of HE grenades held.
    pub he_grenades: i32,
    /// Number of flashbangs held.
    pub flashbangs: i32,
    /// Number of decoy grenades held.
    pub decoy_grenades: i32,
    // ── Economy ──
    /// Value of the player's current equipment (`m_unCurrentEquipmentValue`).
    pub equipment_value: i32,
    /// Equipment value at the start of the round (`m_unRoundStartEquipmentValue`).
    pub equipment_value_round_start: i32,
    /// The player's cash (`m_pInGameMoneyServices.m_iAccount`).
    pub money: i32,
    // ── Status ──
    /// Whether the player is fully crouched (`m_pMovementServices.m_bDucked`).
    pub is_crouched: bool,
    /// Whether the player is walking (moving quietly).
    pub is_walking: bool,
    /// Whether the player is off the ground (airborne — `m_fFlags` `FL_ONGROUND`
    /// clear), i.e. mid-jump or falling.
    pub is_jumping: bool,
    /// Whether the player is currently in a bomb (plant) zone.
    pub is_in_bomb_zone: bool,
    /// Whether the player is scoped in.
    pub is_scoped: bool,
    /// Whether the player is defusing the bomb.
    pub is_defusing: bool,
    /// Seconds of blindness remaining (`m_flFlashDuration`); 0 when not blinded.
    pub flash_duration: f32,
    /// Comma-separated short names of every weapon in the loadout, in slot
    /// order (e.g. `ak47,deagle,knife,hegrenade,flashbang,flashbang`).
    pub inventory: String,
}

/// A team's economy at the start of one round (see [`Parser::round_economy`]).
#[derive(Debug, Clone, serde::Serialize)]
pub struct RoundEconomy {
    pub round_num: i32,
    /// `"terrorist"` / `"counter-terrorist"`.
    pub side: &'static str,
    /// Total equipment value across the team once the buy is locked (freeze end).
    pub equipment_value: i32,
    /// `"eco"` / `"force"` / `"full"` (see `buy_type`).
    pub buy_type: &'static str,
    /// Number of players counted for the team.
    pub n_players: i32,
}

/// A chat message (`SayText` / `SayText2` user message).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct ChatMessage {
    pub tick: i32,
    /// Sender's controller entity index, when the message carries one.
    pub entity_index: Option<i32>,
    pub name: Option<String>,
    pub message: String,
    /// Chat channel, e.g. ``Cstrike_Chat_All`` / ``Cstrike_Chat_T``.
    pub channel: Option<String>,
}

/// A flash event: one player blinded by a thrown flashbang (see
/// [`Parser::blinds`]). The attacker is the flash's thrower — which may be a
/// teammate (a team-flash) or the victim themselves (a self-flash).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct Blind {
    /// Tick the flash detonated and the blind began.
    pub tick: i32,
    pub attacker_steamid: Option<u64>,
    pub attacker_name: Option<String>,
    pub attacker_side: Option<String>,
    pub attacker_x: Option<f32>,
    pub attacker_y: Option<f32>,
    pub attacker_z: Option<f32>,
    pub victim_steamid: Option<u64>,
    pub victim_name: Option<String>,
    pub victim_side: Option<String>,
    pub victim_x: Option<f32>,
    pub victim_y: Option<f32>,
    pub victim_z: Option<f32>,
    /// Blind duration in seconds (`m_flFlashDuration` at onset).
    pub duration: f32,
}

/// A weapon-item transaction (see [`Parser::item_events`]): a purchase, a
/// pickup, or a drop, with the acting player resolved.
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct ItemEvent {
    pub tick: i32,
    /// `purchase`, `pickup`, or `drop`.
    pub action: String,
    pub steamid: Option<u64>,
    pub name: Option<String>,
    pub side: Option<String>,
    /// Short weapon name (e.g. `ak47`, `deagle`, `hegrenade`).
    pub item: String,
    pub x: Option<f32>,
    pub y: Option<f32>,
    pub z: Option<f32>,
    /// Steam id of the weapon's original owner (`m_OriginalOwnerXuid*`) — for a
    /// pickup, whose weapon it originally was; equals `steamid` for a purchase.
    pub original_owner_steamid: Option<u64>,
    /// Money spent, for a `purchase` (the actor's account drop that tick). May
    /// bundle other buys made on the same tick.
    pub cost: Option<i32>,
    /// For a `drop`, whether it was dropped near a buy zone (`m_bDroppedNearBuyZone`).
    pub near_buy_zone: Option<bool>,
}

impl Parser {
    /// Every player seen in the demo — Steam id, name, last observed side, and
    /// the team ("clan") name they were playing under.
    ///
    /// Derived from `CCSPlayerController` entities, so bots appear too (with
    /// `steamid` 0). A reconnecting player gets a fresh controller slot; rows
    /// are deduplicated by Steam id, keeping the freshest state.
    ///
    /// Clan names come from the `CCSTeam` entities, which are keyed by team
    /// number — and team numbers swap sides at halftime. They are therefore read
    /// at the same time as each player's side, so both describe the same moment.
    pub fn players(&self) -> Result<Vec<Player>> {
        let filter: HashSet<&str> = HashSet::from([PLAYER_CONTROLLER_CLASS, TEAM_CLASS]);
        let mut keys: Option<(Option<u64>, Option<u64>, Option<u64>)> = None;
        let mut team_keys: Option<(Option<u64>, Option<u64>)> = None;
        let mut seen: std::collections::BTreeMap<i32, Player> = Default::default();
        // Team number -> clan name, as of the tick being processed.
        let mut clans: HashMap<i64, String> = HashMap::new();
        self.run_to_end_filtered(&filter, |ctx| {
            // Teams first: the controller loop below reads `clans`, and team
            // entities sort after the controllers by entity index.
            let (team_num_key, clan_key) = *team_keys.get_or_insert_with(|| {
                let ser = ctx.serializers.get(TEAM_CLASS);
                let key = |name: &str| ser.and_then(|s| s.resolve_field_key(name));
                (key("m_iTeamNum"), key("m_szClanTeamname"))
            });
            for (_, e) in ctx.entities.iter() {
                if !e.active || e.class_name != TEAM_CLASS {
                    continue;
                }
                let team = e.get_i64(team_num_key);
                // Only the playing sides matter; 0 / 1 are unassigned and
                // spectator, which never carry a clan name.
                if team <= 1 {
                    continue;
                }
                match e.get_string(clan_key) {
                    Some(clan) if !clan.is_empty() => {
                        clans.insert(team, clan);
                    }
                    // An empty string means the server never named this team;
                    // leave any earlier value in place rather than blanking it.
                    _ => {}
                }
            }

            let (steamid_key, name_key, team_key) = *keys.get_or_insert_with(|| {
                let ser = ctx.serializers.get(PLAYER_CONTROLLER_CLASS);
                let key = |name: &str| ser.and_then(|s| s.resolve_field_key(name));
                (key("m_steamID"), key("m_iszPlayerName"), key("m_iTeamNum"))
            });
            for (idx, e) in ctx.entities.iter() {
                if !e.active || e.class_name != PLAYER_CONTROLLER_CLASS {
                    continue;
                }
                let entry = seen.entry(idx).or_default();
                if let Some(steamid) = e.get_u64(steamid_key) {
                    entry.steamid = Some(steamid);
                }
                if let Some(name) = e.get_string(name_key) {
                    entry.name = Some(name);
                }
                let team = e.get_i64(team_key);
                if team > 0 {
                    entry.side = Some(team_name(team).to_string());
                    if let Some(clan) = clans.get(&team) {
                        entry.team_clan_name = Some(clan.clone());
                    }
                }
            }
        })?;

        // Humans dedupe by Steam id; bots (steamid 0, e.g. the GOTV camera
        // controllers) dedupe by name. The freshest state wins either way.
        let mut out: Vec<Player> = Vec::new();
        let mut by_key: HashMap<(u64, Option<String>), usize> = HashMap::new();
        for player in seen.into_values() {
            let key = match player.steamid {
                Some(steamid) if steamid != 0 => (steamid, None),
                _ => (0, player.name.clone()),
            };
            match by_key.get(&key) {
                Some(&i) => out[i] = player,
                None => {
                    by_key.insert(key, out.len());
                    out.push(player);
                }
            }
        }
        Ok(out)
    }

    /// Every player's state at a single tick.
    ///
    /// Seeks to `tick` (via the nearest preceding full packet) and reads each
    /// active player pawn: position, eye angles, health, armor, side, and the
    /// controller's Steam id and name.
    pub fn snapshot(&self, tick: i32) -> Result<Vec<PlayerState>> {
        let ctx = self.parse_to_tick(tick)?;
        let keys = SnapshotKeys::resolve(&ctx);
        Ok(Self::player_states(&ctx, &keys))
    }

    /// Every player's state at a queried set of ticks, in one decode pass.
    ///
    /// The sampled ticks are the union of a periodic stride (`every`, gap-robust
    /// — fires once the tick has advanced at least `every` since the last sample,
    /// so demos that skip tick numbers still yield ~one row per `every`) and the
    /// explicit `ticks` set — all restricted to `[start_tick, end_tick]`. When no
    /// stride and no explicit ticks are given, **every** tick in the window is
    /// emitted (a contiguous range). Rows come out in tick order.
    pub fn snapshots_query(
        &self,
        every: Option<i32>,
        ticks: &HashSet<i32>,
        start_tick: i32,
        end_tick: i32,
    ) -> Result<Vec<PlayerState>> {
        let filter = snapshot_filter();
        let in_window = move |t: i32| t >= start_tick && t <= end_tick;

        // No sampler: every tick in the window (contiguous range).
        if every.is_none() && ticks.is_empty() {
            return self.collect_states(&filter, in_window);
        }

        // Resolve the sampled tick set once, up front, so it does not depend on
        // how the demo is split into parallel segments.
        let mut sampled: HashSet<i32> = ticks.clone();
        if let Some(step) = every {
            let mut last: Option<i32> = None;
            for t in self.distinct_ticks()? {
                if last.is_none_or(|l| t - l >= step) {
                    sampled.insert(t);
                    last = Some(t);
                }
            }
        }
        self.collect_states(&filter, move |t| sampled.contains(&t) && in_window(t))
    }

    /// Collect player-state snapshots for every tick matching `predicate`, in one
    /// pass. Decodes across keyframe segments in parallel (falling back to a
    /// single serial pass when parallelism is disabled) — player pawn/controller
    /// state is re-keyframed at every full packet, so the per-segment cold
    /// restarts stitch back into the same result as a serial pass.
    fn collect_states(
        &self,
        filter: &HashSet<&str>,
        predicate: impl Fn(i32) -> bool + Sync,
    ) -> Result<Vec<PlayerState>> {
        let n = parallel_segment_budget();
        if n <= 1 {
            let mut out = Vec::new();
            let mut keys: Option<SnapshotKeys> = None;
            self.run_to_end_filtered(filter, |ctx| {
                if predicate(ctx.tick) {
                    let keys = keys.get_or_insert_with(|| SnapshotKeys::resolve(ctx));
                    out.extend(Self::player_states(ctx, keys));
                }
            })?;
            return Ok(out);
        }

        let offsets = self.full_packet_offsets()?;
        let n = n.min(offsets.len().max(1));
        let segments = segment_ranges(&offsets, n);
        let (predicate, this) = (&predicate, self);
        let parts: Vec<Vec<PlayerState>> = std::thread::scope(|s| {
            let handles: Vec<_> = segments
                .iter()
                .map(|&(seg_start, seg_end)| {
                    s.spawn(move || -> Result<Vec<PlayerState>> {
                        let mut out = Vec::new();
                        let mut keys: Option<SnapshotKeys> = None;
                        this.decode_segment(seg_start, seg_end, filter, |ctx| {
                            if predicate(ctx.tick) {
                                let keys = keys.get_or_insert_with(|| SnapshotKeys::resolve(ctx));
                                out.extend(Self::player_states(ctx, keys));
                            }
                        })?;
                        Ok(out)
                    })
                })
                .collect();
            handles
                .into_iter()
                .map(|h| h.join().expect("snapshot segment panicked"))
                .collect::<Result<Vec<_>>>()
        })?;
        Ok(parts.into_iter().flatten().collect())
    }

    /// Per-team economy and buy type for each round.
    ///
    /// One row per (round, side): the side's total equipment value once the buy
    /// is locked (read at freeze end) and its `buy_type` classification. Reuses
    /// the sampled-snapshot pass over the rounds' freeze-end ticks. Knife rounds
    /// are excluded.
    pub fn round_economy(&self) -> Result<Vec<RoundEconomy>> {
        let rounds = self.rounds()?;
        // Freeze-end tick per round → its index. Knife rounds are skipped: their
        // "buy" is meaningless, and CS2 often numbers the knife round the same as
        // the real first round.
        let mut tick_to_round: HashMap<i32, usize> = HashMap::new();
        let mut ticks: HashSet<i32> = HashSet::new();
        for (i, r) in rounds.iter().enumerate() {
            if r.is_knife_round {
                continue;
            }
            let t = r.freeze_end_tick.or(r.start_tick).unwrap_or(r.end_tick);
            tick_to_round.insert(t, i);
            ticks.insert(t);
        }
        let states = self.snapshots_query(None, &ticks, i32::MIN, i32::MAX)?;

        // (round index, side) -> (equipment sum, player count), plus each round's
        // per-player side, for detecting the halftime side switch below.
        let mut agg: HashMap<(usize, &'static str), (i32, i32)> = HashMap::new();
        let mut round_sides: HashMap<usize, HashMap<u64, &'static str>> = HashMap::new();
        for s in &states {
            if let (Some(&round), Some(side)) = (tick_to_round.get(&s.tick), s.side) {
                // Current equipment at freeze end is the finished buy (the
                // round-start field is the pre-buy carry-over).
                let e = agg.entry((round, side)).or_insert((0, 0));
                e.0 += s.equipment_value;
                e.1 += 1;
                if let Some(steamid) = s.steamid {
                    round_sides.entry(round).or_default().insert(steamid, side);
                }
            }
        }

        // Pistol rounds: the first round played, plus the first round whose sides
        // are flipped from the previous one (the halftime switch). Overtime's
        // later switches aren't pistols — their equipment classifies normally.
        let mut ordered: Vec<usize> = round_sides.keys().copied().collect();
        ordered.sort_unstable();
        let mut pistol_rounds: HashSet<usize> = ordered.first().copied().into_iter().collect();
        for pair in ordered.windows(2) {
            if sides_flipped(&round_sides[&pair[0]], &round_sides[&pair[1]]) {
                pistol_rounds.insert(pair[1]);
                break;
            }
        }

        let mut out: Vec<RoundEconomy> = agg
            .into_iter()
            .map(
                |((round, side), (equipment_value, n_players))| RoundEconomy {
                    round_num: rounds[round].round_num,
                    side,
                    equipment_value,
                    buy_type: if pistol_rounds.contains(&round) {
                        "pistol"
                    } else {
                        buy_type(equipment_value)
                    },
                    n_players,
                },
            )
            .collect();
        out.sort_by_key(|r| (r.round_num, r.side));
        Ok(out)
    }

    /// The ticks on which any of the named game events fired, for feeding
    /// [`Self::snapshots_query`] (resolving event names to ticks once, from the
    /// cached event stream).
    pub fn event_ticks(&self, names: &HashSet<&str>) -> Result<HashSet<i32>> {
        Ok(self
            .events_ref()?
            .iter()
            .filter(|e| names.contains(e.name.as_str()))
            .map(|e| e.tick)
            .collect())
    }

    /// Read every active player pawn's state out of a parsed context, using
    /// field keys resolved once (see [`SnapshotKeys`]) rather than per tick.
    fn player_states(ctx: &Context, keys: &SnapshotKeys) -> Vec<PlayerState> {
        let (pk, ck) = (&keys.pawn, &keys.ctrl);
        let mut out = Vec::new();
        for (_, pawn) in ctx.entities.iter() {
            if !pawn.active || pawn.class_id != keys.pawn_class {
                continue;
            }
            let mut state = PlayerState {
                tick: ctx.tick,
                ..Default::default()
            };
            // Position is only meaningful once the offset fields are present.
            if pk.offset[0].is_some_and(|k| pawn.fields.contains_key(&k)) {
                let [x, y, z] = pawn.world_position(pk.cell, pk.offset);
                (state.x, state.y, state.z) = (Some(x), Some(y), Some(z));
            }
            let angles = pawn.get_qangle(keys.angles);
            state.pitch = angles[0];
            state.yaw = angles[1];
            state.health = pawn.get_i64(keys.health) as i32;
            state.armor = pawn.get_i64(keys.armor) as i32;
            state.equipment_value = pawn.get_i64(keys.equip) as i32;
            state.equipment_value_round_start = pawn.get_i64(keys.equip_round_start) as i32;
            state.has_helmet = pawn.get_bool(keys.has_helmet);
            state.has_defuser = pawn.get_bool(keys.has_defuser);
            state.is_crouched = pawn.get_bool(keys.crouched);
            state.is_walking = pawn.get_bool(keys.walking);
            // `FL_ONGROUND` clear ⇒ airborne (mid-jump or falling).
            state.is_jumping = pawn
                .get_u64(keys.flags)
                .is_some_and(|f| f as u32 & FL_ONGROUND == 0);
            state.is_in_bomb_zone = pawn.get_bool(keys.in_bomb_zone);
            state.is_scoped = pawn.get_bool(keys.scoped);
            state.is_defusing = pawn.get_bool(keys.defusing);
            state.flash_duration = pawn.get_f32(keys.flash);
            state.active_weapon = pawn
                .get_handle(keys.active_weapon)
                .and_then(|h| ctx.entities.get_by_handle(h))
                .and_then(|w| weapon_info(&w.class_name))
                .map(|i| i.name);
            let count = (pawn.get_i64(keys.weapon_count) as usize).min(keys.weapons.len());
            fill_loadout(ctx, pawn, &keys.weapons[..count], &mut state);
            // Skip reserve/uninitialized pawns: the engine keeps spare
            // `CCSPlayerPawn` entities that sit at the world origin with no team.
            // A pawn in play is always on T or CT — dead players keep their team
            // — so a real team assignment is the reliable signal. (Don't gate on
            // the controller: a live player's controller can momentarily fail to
            // resolve, leaving a real row with no Steam id or name.)
            let team = pawn.get_i64(pk.team);
            if team <= 0 {
                continue;
            }
            state.side = Some(team_name(team));
            if let Some(ctrl) = pawn
                .get_handle(pk.controller)
                .and_then(|h| ctx.entities.get_by_handle(h))
            {
                state.steamid = ctrl.get_u64(ck.steamid);
                state.name = ctrl.get_string(ck.name);
                state.money = ctrl.get_i64(ck.money) as i32;
            }
            out.push(state);
        }
        out
    }

    /// Chat messages (`SayText` / `SayText2` user messages), in tick order.
    pub fn chat(&self) -> Result<Vec<ChatMessage>> {
        use awpy_proto::proto::{
            CUserMessageSayText, CUserMessageSayText2, EBaseUserMessages, ECstrike15UserMessages,
        };
        use prost::Message as _;

        let say_text = [
            EBaseUserMessages::UmSayText as u32,
            ECstrike15UserMessages::CsUmSayText as u32,
        ];
        let say_text2 = [
            EBaseUserMessages::UmSayText2 as u32,
            ECstrike15UserMessages::CsUmSayText2 as u32,
        ];

        let mut out = Vec::new();
        for event in self.events_ref()? {
            if say_text2.contains(&event.msg_type) {
                let Ok(msg) = CUserMessageSayText2::decode(&event.payload[..]) else {
                    continue;
                };
                out.push(ChatMessage {
                    tick: event.tick,
                    entity_index: msg.entityindex.filter(|&i| i >= 0),
                    name: msg.param1.filter(|s| !s.is_empty()),
                    message: msg.param2.unwrap_or_default(),
                    channel: msg.messagename.filter(|s| !s.is_empty()),
                });
            } else if say_text.contains(&event.msg_type) {
                let Ok(msg) = CUserMessageSayText::decode(&event.payload[..]) else {
                    continue;
                };
                out.push(ChatMessage {
                    tick: event.tick,
                    entity_index: msg.playerindex.filter(|&i| i >= 0),
                    name: None,
                    message: msg.text.unwrap_or_default(),
                    channel: None,
                });
            }
        }
        Ok(out)
    }

    /// Flash events: one row per player blinded, with the thrower, the victim,
    /// and the blind duration.
    ///
    /// CS2 GOTV demos generally omit the `player_blind` game event (as they omit
    /// chat and round events), so this reconstructs blinds from entity state
    /// instead, which works on every demo. A blind is a rising edge of a pawn's
    /// networked `m_flFlashDuration` — the value at the edge is the blind's
    /// duration in seconds and the pawn is the victim. The thrower is taken from
    /// the `flashbang_detonate` game event on the same tick (blind onsets and
    /// detonations are simultaneous); when several flashes pop on one tick, each
    /// victim is attributed to the nearest detonation by world position.
    ///
    /// Like [`Parser::kills`], this performs a filtered entity decode — built
    /// alongside kills / damages / bomb in [`Parser::event_datasets`].
    pub fn blinds(&self) -> Result<Vec<Blind>> {
        Ok(self.event_datasets()?.blinds)
    }

    /// Weapon-item transactions — purchases, pickups, and drops — reconstructed
    /// from entity state, so they work on demos that omit the `item_purchase`
    /// game event (GOTV/broadcast demos strip it).
    ///
    /// Each player's `m_hMyWeapons` inventory is tracked across ticks: a weapon
    /// entering it is an acquisition, one leaving it is a release. An
    /// acquisition is a **purchase** when the actor's money drops on that tick,
    /// otherwise a **pickup** (a teammate's / enemy's weapon, or their own
    /// dropped one). A release is a **drop** when the weapon is left on the
    /// ground (still a live entity with no owner); a thrown grenade — whose held
    /// entity is consumed — is not a drop. Free default spawn equipment is not
    /// reported (and the knife is excluded entirely). The decode is filtered to
    /// player pawn/controller and known weapon classes.
    pub fn item_events(&self) -> Result<Vec<ItemEvent>> {
        /// Field keys on a weapon serializer, resolved once per class.
        struct WeaponKeys {
            owner: Option<u64>,
            xuid_low: Option<u64>,
            xuid_high: Option<u64>,
            dropped_time: Option<u64>,
            near_buy_zone: Option<u64>,
        }

        /// Combine the split `m_OriginalOwnerXuid{Low,High}` into a Steam id.
        fn original_owner(w: &Entity, wk: &WeaponKeys) -> Option<u64> {
            let id = ((w.get_u32(wk.xuid_high) as u64) << 32) | w.get_u32(wk.xuid_low) as u64;
            (id > 0).then_some(id)
        }

        let mut inv: HashMap<i32, HashSet<u32>> = HashMap::new();
        let mut prev_money: HashMap<u64, i32> = HashMap::new();
        let mut weapon_keys: HashMap<String, WeaponKeys> = HashMap::new();
        let mut pk: Option<PawnKeys> = None;
        let mut ck: Option<CtrlKeys> = None;
        let mut money_key: Option<Option<u64>> = None;
        let mut count_key: Option<Option<u64>> = None;
        let mut slot_keys: Option<Vec<Option<u64>>> = None;
        let mut out: Vec<ItemEvent> = Vec::new();

        let filter = snapshot_filter();
        self.run_to_end_filtered(&filter, |ctx| {
            let pkr = pk.get_or_insert_with(|| PawnKeys::resolve(ctx));
            let ckr = ck.get_or_insert_with(|| CtrlKeys::resolve(ctx));
            let mkey = *money_key.get_or_insert_with(|| {
                ctx.serializers
                    .get(PLAYER_CONTROLLER_CLASS)
                    .and_then(|s| s.resolve_field_key("m_pInGameMoneyServices.m_iAccount"))
            });
            let pawn_ser = ctx.serializers.get(PLAYER_PAWN_CLASS);
            let ckey = *count_key.get_or_insert_with(|| {
                pawn_ser.and_then(|s| s.resolve_field_key("m_pWeaponServices.m_hMyWeapons"))
            });
            let skeys = slot_keys.get_or_insert_with(|| {
                (0..MAX_INVENTORY)
                    .map(|i| {
                        pawn_ser.and_then(|s| {
                            s.resolve_field_key(&format!("m_pWeaponServices.m_hMyWeapons.{i}"))
                        })
                    })
                    .collect()
            });

            // Resolve the field keys for a weapon's serializer.
            let keys_for = |class: &str| -> WeaponKeys {
                let s = ctx.serializers.get(class);
                let key = |n: &str| s.and_then(|s| s.resolve_field_key(n));
                WeaponKeys {
                    owner: key("m_hOwnerEntity"),
                    xuid_low: key("m_OriginalOwnerXuidLow"),
                    xuid_high: key("m_OriginalOwnerXuidHigh"),
                    dropped_time: key("m_flDroppedAtTime"),
                    near_buy_zone: key("m_bDroppedNearBuyZone"),
                }
            };

            for (idx, pawn) in ctx.entities.iter() {
                if !pawn.active || pawn.class_name != PLAYER_PAWN_CLASS {
                    continue;
                }
                let actor = resolve_from_pawn(ctx, pawn, pkr, ckr);

                // Current inventory: the live `m_hMyWeapons` handles.
                let count = (pawn.get_i64(ckey) as usize).min(skeys.len());
                let mut cur: HashSet<u32> = HashSet::new();
                for &sk in &skeys[..count] {
                    if let Some(h) = pawn.get_handle(sk) {
                        cur.insert(h);
                    }
                }
                let prev = inv.remove(&idx).unwrap_or_default();

                // Without a Steam id we cannot classify or key money; keep the
                // inventory current so a later resolved tick diffs cleanly.
                let Some(steamid) = actor.steamid else {
                    inv.insert(idx, cur);
                    continue;
                };

                // Money change for this player this tick (purchases spend money).
                let account = pawn
                    .get_handle(pkr.controller)
                    .and_then(|h| ctx.entities.get_by_handle(h))
                    .map(|c| c.get_i64(mkey) as i32);
                let delta = match (account, prev_money.get(&steamid)) {
                    (Some(a), Some(&p)) => a - p,
                    _ => 0,
                };
                if let Some(a) = account {
                    prev_money.insert(steamid, a);
                }

                // Acquisitions.
                for &h in cur.difference(&prev) {
                    let Some(weapon) = ctx.entities.get_by_handle(h) else {
                        continue;
                    };
                    let Some(info) = weapon_info(&weapon.class_name) else {
                        continue;
                    };
                    if info.slot == WeaponSlot::Melee {
                        continue;
                    }
                    let wk = weapon_keys
                        .entry(weapon.class_name.clone())
                        .or_insert_with(|| keys_for(&weapon.class_name));
                    let orig = original_owner(weapon, wk);
                    let dropped = weapon.get_f32(wk.dropped_time) > 0.0;
                    // Free default items (side pistols, bomb) are never bought;
                    // their grant coincides with a money reset, so gate them out
                    // of the purchase branch. A large drop is likewise a reset.
                    let buyable = !FREE_DEFAULT_ITEMS.contains(&info.name);
                    let (action, cost) = if buyable && delta < 0 && -delta <= MAX_PURCHASE_COST {
                        ("purchase", Some(-delta))
                    } else if orig != Some(steamid) || dropped {
                        // Someone else's weapon, or your own previously-dropped
                        // one — a real pickup. Free fresh self-owned gear is the
                        // default spawn loadout, which we skip.
                        ("pickup", None)
                    } else {
                        continue;
                    };
                    out.push(ItemEvent {
                        tick: ctx.tick,
                        action: action.to_string(),
                        steamid: actor.steamid,
                        name: actor.name.clone(),
                        side: actor.side.clone(),
                        item: info.name.to_string(),
                        x: actor.x,
                        y: actor.y,
                        z: actor.z,
                        original_owner_steamid: orig,
                        cost,
                        near_buy_zone: None,
                    });
                }

                // Releases: a weapon left on the ground (live entity, no owner)
                // is a drop; a consumed one (thrown grenade) is skipped.
                for &h in prev.difference(&cur) {
                    let Some(weapon) = ctx.entities.get_by_handle(h) else {
                        continue;
                    };
                    let Some(info) = weapon_info(&weapon.class_name) else {
                        continue;
                    };
                    if info.slot == WeaponSlot::Melee {
                        continue;
                    }
                    let wk = weapon_keys
                        .entry(weapon.class_name.clone())
                        .or_insert_with(|| keys_for(&weapon.class_name));
                    let still_held = weapon
                        .get_handle(wk.owner)
                        .and_then(|oh| ctx.entities.get_by_handle(oh))
                        .is_some_and(|o| o.class_name.contains("PlayerPawn"));
                    if still_held {
                        continue;
                    }
                    out.push(ItemEvent {
                        tick: ctx.tick,
                        action: "drop".to_string(),
                        steamid: actor.steamid,
                        name: actor.name.clone(),
                        side: actor.side.clone(),
                        item: info.name.to_string(),
                        x: actor.x,
                        y: actor.y,
                        z: actor.z,
                        original_owner_steamid: original_owner(weapon, wk),
                        cost: None,
                        near_buy_zone: Some(weapon.get_bool(wk.near_buy_zone)),
                    });
                }

                inv.insert(idx, cur);
            }
        })?;

        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ev(name: &str, tick: i32, keys: &[(&str, &str)]) -> GameEvent {
        GameEvent {
            tick,
            name: name.to_string(),
            msg_type: 0,
            keys: keys
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect(),
            payload: Vec::new(),
        }
    }

    #[test]
    fn keys_typed_getters() {
        let e = ev("player_death", 10, &[("userid", "7"), ("headshot", "true")]);
        let k = Keys(&e.keys);
        assert_eq!(k.i32("userid"), 7);
        assert_eq!(k.i64("userid"), 7);
        assert!(k.bool("headshot"));
        assert_eq!(k.i32("missing"), 0);
        assert!(!k.bool("missing"));
        assert_eq!(k.string("userid"), "7");
    }

    #[test]
    fn damage_event_fields_reconstructs_health() {
        let e = ev(
            "player_hurt",
            50,
            &[
                ("userid", "5"),
                ("attacker", "10"),
                ("health", "75"),
                ("armor", "90"),
                ("weapon", "glock"),
                ("dmg_health", "25"),
                ("dmg_armor", "10"),
                ("hitgroup", "3"),
            ],
        );
        let dmg = damage_event_fields(&e);
        assert_eq!(dmg.tick, 50);
        assert_eq!(dmg.weapon, "glock");
        assert_eq!(dmg.hitgroup_name, "stomach");
        assert_eq!(dmg.dmg_health, 25);
        // pre = post + damage
        assert_eq!(dmg.health_post, 75);
        assert_eq!(dmg.health_pre, 100);
        assert_eq!(dmg.armor_post, 90);
        assert_eq!(dmg.armor_pre, 100);
        // Player fields are unresolved until an entity pass fills them.
        assert!(dmg.attacker_name.is_none());
    }

    #[test]
    fn damage_overkill_clamps_pre_health() {
        // A lethal hit reports raw (uncapped) damage, so post + dmg can exceed
        // 100; pre-health must clamp to the 100 HP maximum.
        let e = ev("player_hurt", 10, &[("health", "0"), ("dmg_health", "444")]);
        let dmg = damage_event_fields(&e);
        assert_eq!(dmg.dmg_health, 444); // raw damage is preserved
        assert_eq!(dmg.health_post, 0);
        assert_eq!(dmg.health_pre, 100); // clamped, not 444
    }

    fn kill(tick: i32, attacker: u64, aside: &str, victim: u64, vside: &str) -> Kill {
        Kill {
            tick,
            attacker_steamid: Some(attacker),
            attacker_side: Some(aside.into()),
            victim_steamid: Some(victim),
            victim_side: Some(vside.into()),
            ..Default::default()
        }
    }

    const T: &str = "terrorist";
    const CT: &str = "counter-terrorist";

    #[test]
    fn trade_flags_are_duals() {
        // CT 2 kills T 1; T 3 trades by killing CT 2 inside the window. The first
        // kill's victim was traded, and the second kill *is* that trade.
        let kills = vec![kill(100, 2, CT, 1, T), kill(300, 3, T, 2, CT)];
        let flags = trade_flags(&kills, 320);
        assert_eq!(flags[0], (false, true));
        assert_eq!(flags[1], (true, false));
    }

    #[test]
    fn trade_flags_respect_the_window() {
        let kills = vec![kill(100, 2, CT, 1, T), kill(500, 3, T, 2, CT)];
        let flags = trade_flags(&kills, 320); // 400 ticks apart, window is 320
        assert_eq!(flags, vec![(false, false), (false, false)]);
    }

    #[test]
    fn a_teammates_revenge_is_required_for_a_trade() {
        // CT 2 kills T 1, then a *fellow CT* kills CT 2 (a team kill). Nobody on
        // T's side avenged the death, so it is not traded.
        let kills = vec![kill(100, 2, CT, 1, T), kill(200, 4, CT, 2, CT)];
        let flags = trade_flags(&kills, 320);
        assert_eq!(flags[0], (false, false));
        assert_eq!(flags[1], (false, false));
    }

    #[test]
    fn trade_flags_follow_ticks_not_input_order() {
        // Same two kills as `trade_flags_are_duals`, supplied out of tick order:
        // the flags must attach to the same kills, positionally.
        let kills = vec![kill(300, 3, T, 2, CT), kill(100, 2, CT, 1, T)];
        let flags = trade_flags(&kills, 320);
        assert_eq!(flags[0], (true, false)); // the tick-300 revenge kill
        assert_eq!(flags[1], (false, true)); // the tick-100 death it avenged
    }

    #[test]
    fn a_death_with_an_unresolved_side_cannot_be_traded() {
        // World / suicide deaths have no victim side, so there is no team to
        // credit a revenge kill to.
        let mut kills = vec![kill(100, 2, CT, 1, T), kill(200, 3, T, 2, CT)];
        kills[0].victim_side = None;
        let flags = trade_flags(&kills, 320);
        assert_eq!(flags[0], (false, false));
        assert_eq!(flags[1], (false, false));
    }
}
