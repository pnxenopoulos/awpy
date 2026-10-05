# Datasets

Dataset properties on `Demo` return cached Polars DataFrames with typed columns.

## Batch loading

Use `Demo.load()` when an analysis needs several datasets:

```python
demo.load("players", "stats")
players = demo.players
stats = demo.stats
```

The method returns `None` and caches the requested DataFrames.
It validates all names before decoding and skips cached datasets.
Use `Demo.available_datasets()` to list valid names.

Requested event datasets share one pass, as do requested `grenades`, `fires`,
and `smokes`. Stats reuse combat, round, and roster inputs.
A combined stats request can also collect bomb and shot rows in that pass.
Direct property access prepares its compatible event or projectile group.
Use `load()` to restrict collection to a known set.

Entity rows expose a slot (`entity_id`) and generation (`entity_serial`).
Use both as the identity: the engine can reuse slots after deletion.

All Steam ID columns use Polars `UInt64`, including columns that are empty or
contain only null values. Keep this type when you join datasets. To convert a
dataset to pandas without a floating-point conversion, use Arrow extension
arrays:

```python
pandas_kills = demo.kills.to_pandas(use_pyarrow_extension_array=True)
```

This conversion requires `pyarrow`. The default NumPy-backed pandas conversion
cannot represent nullable integers and can change a nullable Steam ID column to
`float64`.

## `rounds`

```python
demo.rounds
```

One row per round, reconstructed from `CCSGameRules`.
Round events are not required. Overtime rounds are included.

| Column | Type | Description |
| --- | --- | --- |
| `round_num` | i32 | 1-indexed round number (`m_totalRoundsPlayed` at round end). |
| `start_tick` | i32? | Tick the round's freeze time began (null if not observed). |
| `freeze_end_tick` | i32? | Tick freeze time ended and play began. |
| `end_tick` | i32 | Tick the round was decided (a winner was set). |
| `official_end_tick` | i32? | Tick the round *officially* ended (post-round reset, ≈ the next round's freeze start); null for the last round. |
| `winner` | i32 | Winning team number (2 = terrorist, 3 = counter-terrorist). |
| `winner_side` | str | Winning side name. |
| `reason` | i32 | Raw round-end reason code (`RoundEndReason_t`). |
| `reason_name` | str | Human-readable reason (e.g. `bomb_defused`, `ct_win`). |
| `is_knife_round` | bool | Whether this is a knife round — a side-decider round where every kill is a melee (knife) kill, with no firearm or grenade kills. Excluded from `stats` by default. |

```python
# Final score by side
demo.rounds.group_by("winner_side").len()
```

## `kills`

```python
demo.kills
```

One row per `player_death` event. Entity decoding resolves participants and
positions, so this costs more than reading raw events.

For each of `attacker`, `victim`, `assister`:

| Column | Type | Description |
| --- | --- | --- |
| `<who>_entity_id` | i32? | Player-pawn entity slot. |
| `<who>_entity_serial` | u32? | Player-pawn entity generation. |
| `<who>_steamid` | u64? | 64-bit Steam id (from the controller's `m_steamID`). |
| `<who>_name` | str? | Display name (`m_iszPlayerName`). |
| `<who>_side` | str? | `terrorist` / `counter-terrorist`. |
| `<who>_x` / `_y` / `_z` | f32? | World position (Hammer units) at the kill tick. |

Plus the kill's own fields: `weapon` (str), `headshot` (bool), `dominated`,
`noscope` (bool), `penetrated`, `revenge`, `thrusmoke` (bool), `hitgroup`,
`hitgroup_name`, `is_trade` (bool), `victim_traded` (bool), and `tick`.

Participant columns are null if the participant is absent or cannot be resolved.

### Trades

Two flags mark each kill's place in a trade. A **trade** is a kill that avenges a
teammate killed within the last 5 seconds:

| Column | Description |
| --- | --- |
| `is_trade` | This kill **is** a trade — the attacker killed someone who had just killed one of their teammates. |
| `victim_traded` | This kill's **victim was traded** — a teammate of the victim killed this attacker within the window. |

The revenge kill has `is_trade`; the earlier death has `victim_traded`.
Stats count `victim_traded` as `traded_deaths`.
The totals can differ because one kill can avenge several deaths.
A kill can have both flags.

```python
# Headshot rate per weapon
kills = demo.kills
kills.group_by("weapon").agg(
    total=pl.len(),
    hs_rate=pl.col("headshot").mean(),
).sort("total", descending=True)

# Kills by side
kills.group_by("attacker_side").len()

# Who trades for their team the most?
kills.filter(pl.col("is_trade")).group_by("attacker_name").len().sort("len", descending=True)

# How often does each player's death go unavenged?
kills.group_by("victim_name").agg(
    deaths=pl.len(),
    traded=pl.col("victim_traded").sum(),
).with_columns(trade_rate=pl.col("traded") / pl.col("deaths"))
```

## `damages`

```python
demo.damages
```

One row per `player_hurt` game event, with the attacker and victim resolved to a
Steam id, name, side, and world position (like `kills`), plus the victim's
health/armor before and after the hit.

For each of `attacker`, `victim`: `<who>_entity_id`, `<who>_entity_serial`,
`<who>_steamid`, `<who>_name`, `<who>_side`, and `<who>_x` / `_y` / `_z`.
Other columns: `weapon`, `dmg_health`, `dmg_armor`, `hitgroup`, `hitgroup_name`,
`health_pre`, `health_post`, `armor_pre`, `armor_post`, and `tick`.
Pre-hit values are `post + damage`, capped at 100.
Raw damage can exceed the victim's remaining health.

## `bomb`

```python
demo.bomb
```

Bomb actions with the acting player and their position. Columns: `tick`,
`event` (one of `pickup`, `drop`, `start_plant`, `interrupt_plant`,
`finish_plant`, `defuse`), `entity_id`, `entity_serial`, `steamid`, `name`,
`bombsite` (`A` / `B`; null before the plant), `x`, `y`, `z`.

`start_plant` and `interrupt_plant` rows require the corresponding events.

## `grenades`

```python
demo.grenades
```

Thrown-grenade **trajectories** — one row per tick each grenade projectile is in
flight (samples stop once it settles). Columns: `tick`, `thrower_name`,
`thrower_steamid`, `thrower_side`, `type` (`smoke` / `he` / `flashbang` /
`molotov` / `decoy`), `entity_id`, `entity_serial`, `x`, `y`, `z`.

## `fires` / `smokes`

```python
demo.fires    # burning infernos (molotov / incendiary)
demo.smokes   # deployed smoke clouds
```

**One row per fire / smoke.** Columns: `start_tick`, `end_tick`,
`thrower_name`, `thrower_steamid`, `thrower_side`, `entity_id`,
`entity_serial`, `x`, `y`, `z`. `fires` also has a `type` column.

The window is the game's own event pair, not the (longer) entity lifetime:
`inferno_startburn` → `inferno_expire` for fires (the ~7 s burn, cut short when a
molotov is smoked out) and `smokegrenade_detonate` → `smokegrenade_expired` for
smokes (the deployed cloud, excluding the throw).

Use an interval join to find player samples during fires.
Apply a spatial filter to test whether a player was inside a fire:

```python
import polars as pl

pos = demo.snapshots(start_tick=demo.fires["start_tick"].min(), end_tick=demo.fires["end_tick"].max())
in_fire = pos.join_where(
    demo.fires,
    pl.col("tick") >= pl.col("start_tick"),
    pl.col("tick") <= pl.col("end_tick"),
)
```

## `shots`

```python
demo.shots
```

One row per `weapon_fire` event, with the shooter's state and active-weapon
state. Columns: `tick`, `entity_id`, `entity_serial`, `steamid`, `name`, `side`,
`x`, `y`, `z`, `pitch`, `yaw`, `weapon`, `scoped`, `inaccuracy` (the
weapon's networked accuracy penalty), and `num_bullets_remaining` (active
weapon's clip).

## `blinds`

```python
demo.blinds
```

One row per **flash event** — a player blinded by a flashbang — resolved like
`kills`: the `attacker` (the flash's thrower) and `victim` (the blinded player)
each get a Steam id, name, side, and world position, plus a `duration`.

| Column | Type | Description |
| --- | --- | --- |
| `tick` | i32 | Tick the flash detonated and the blind began. |
| `attacker_steamid` / `_name` / `_side` / `_x` / `_y` / `_z` | | The flash's thrower. |
| `attacker_entity_id` / `attacker_entity_serial` | | The thrower's pawn identity. |
| `victim_entity_id` / `victim_entity_serial` | | The blinded pawn's identity. |
| `victim_steamid` / `_name` / `_side` / `_x` / `_y` / `_z` | | The blinded player. |
| `duration` | f32 | Blind duration in seconds. |

The attacker may be a teammate (a team-flash) or the victim themselves (a
self-flash), so filter on `attacker_side` / `victim_side` or compare Steam ids
as needed.

Awpy reconstructs blinds from increases in a pawn's flash duration.
It attributes the flash to a `flashbang_detonate` event on the same tick.
Without those events, the result is empty.

```python
# Enemy flashes only, longest first
import polars as pl
demo.blinds.filter(pl.col("attacker_side") != pl.col("victim_side")).sort(
    "duration", descending=True
)
```

## `item_events`

```python
demo.item_events
```

Weapon-item transactions — **purchases, pickups, and drops** — one row each,
with the acting player resolved.

| Column | Type | Description |
| --- | --- | --- |
| `tick` | i32 | Tick the transaction occurred. |
| `action` | str | `purchase`, `pickup`, or `drop`. |
| `entity_id` / `entity_serial` | | The acting player's pawn identity. |
| `steamid` / `name` / `side` | | The acting player. |
| `item` | str | Short weapon name (e.g. `ak47`, `deagle`, `hegrenade`). |
| `x` / `y` / `z` | f32? | The player's world position. |
| `original_owner_steamid` | u64? | Steam id of the weapon's original owner. For a `pickup`, whose weapon it originally was; equals `steamid` for a `purchase`. |
| `cost` | i32? | Money spent, for a `purchase` (null otherwise). May bundle other buys made on the same tick. |
| `near_buy_zone` | bool? | For a `drop`, whether it was dropped near a buy zone (e.g. dropping a weapon for a teammate); null otherwise. |

Awpy tracks each player's inventory (`m_hMyWeapons`).
An acquired weapon is a purchase if money decreases on that tick; otherwise,
it is a pickup. A weapon left on the ground is a drop.
Thrown grenades, knives, and free default equipment are excluded.

Scope is weapon-type items (guns, pistols, grenades, C4, taser). Armor, helmet,
and defuser purchases are not included (they are pawn fields, not weapon
entities). Note that C4 pickups/drops also appear, in resolved form, in the
`bomb` dataset.

```python
# Every player's buy on the pistol round
import polars as pl
r1 = demo.rounds.row(0, named=True)
demo.item_events.filter(
    (pl.col("action") == "purchase")
    & (pl.col("tick") >= r1["start_tick"])
    & (pl.col("tick") <= r1["freeze_end_tick"])
).select("name", "item", "cost")

# Guns picked up off the ground (someone else's weapon)
demo.item_events.filter(
    (pl.col("action") == "pickup")
    & (pl.col("original_owner_steamid") != pl.col("steamid"))
)
```

## `stats`

```python
demo.stats
```

One row per player, aggregating the kill / damage / round datasets into the
common scoreboard metrics. Columns: `steamid`, `name`, `rounds_played`, `kills`,
`deaths`, `assists`, `flash_assists`, `headshot_kills`, `headshot_pct`,
`opening_kills`, `opening_deaths`, `traded_deaths`, `multikill_2k` …
`multikill_5k`, `kast`, `adr`, clutches (`clutches_played`, `clutches_won`,
`clutch_1v1` … `clutch_1v5`), plus utility: `utility_damage`, `flashes_thrown`,
`enemies_flashed`, `flash_duration_dealt`.

See {doc}`reference` for metric definitions.
KAST is the percentage of rounds with a kill, assist, survival, or traded death.
ADR is the average enemy health removed per round.

Every player is treated as having played every round (the denominator for KAST
and ADR is the match's round count), so players who join or leave mid-match are
approximate.

Knife rounds are excluded from counts and denominators by default.
Set `include_knife_rounds=True` to include them:

```python
demo.stats                                    # excludes knife rounds (default)
demo.player_stats(include_knife_rounds=True)  # counts them
```

**Both forms are cached.** `demo.stats` and
`demo.player_stats(include_knife_rounds=False)` return the same cached default
result. The `include_knife_rounds=True` variant reuses the decoded combat and
round inputs, then caches its aggregated DataFrame separately.

```python
# Top fraggers with KAST and ADR
demo.stats.sort("kills", descending=True).select("name", "kills", "kast", "adr")

# Clutch success rate
demo.stats.filter(pl.col("clutches_played") > 0).select(
    "name", "clutches_won", "clutches_played",
    rate=pl.col("clutches_won") / pl.col("clutches_played"),
).sort("rate", descending=True)
```

## `round_economy`

```python
demo.round_economy
```

One row per (round, side), with equipment value at freeze end and buy type. Columns: `round_num`,
`side`, `equipment_value`, `buy_type`, `n_players`. `buy_type` is `pistol` / `eco`
/ `force` / `full` — see the {doc}`Reference <reference>` for the thresholds and
how pistol rounds are detected. (This is the *current* equipment at freeze end —
the finished buy; the `equipment_value_round_start` snapshot column is the pre-buy
carry-over.) Knife rounds are excluded.

```python
# Full-buy rounds
demo.round_economy.filter(pl.col("buy_type") == "full")
```

## `players`

```python
demo.players  # steamid, name, side, team_clan_name
```

The roster: one row per player seen in the demo. `side` is the last team the
player was observed on (players swap at halftime); bots (e.g. the GOTV camera
controller) have `steamid` 0.

`team_clan_name` comes from `CCSTeam` entities and is null if not set.
It is recorded with `side`, so players who leave retain their last team name.

```python
# Group a match's players by organization
demo.players.drop_nulls("team_clan_name").group_by("team_clan_name").agg("name")

# Join team names onto the scoreboard
demo.stats.join(
    demo.players.select("steamid", "team_clan_name"), on="steamid", how="left"
).sort("kills", descending=True)
```

## `chat`

```python
demo.chat  # tick, entity_index, name, message, channel
```

Chat messages from `SayText`, `SayText2`, and `SayTextChannel`.
`channel` identifies the chat channel, such as `Cstrike_Chat_All`.
The DataFrame is empty if no supported chat messages are recorded.
The absence of chat entries in `demo.events` does not establish this:
user messages and game events are different streams.

## `convars`

```python
demo.convars                  # -> dict[str, str]
demo.convars["mp_maxrounds"]  # -> "24"
```

Server console variables collected from the demo stream — useful for round
math (`mp_maxrounds`, `mp_freezetime`, `mp_overtime_enable`) and for telling
match formats apart programmatically.

## Game state: `snapshots`

```python
demo.snapshots(ticks=29000)                       # one moment
demo.snapshots(ticks=[29000, 30000, 31000])       # specific ticks
demo.snapshots(start_tick=29000, end_tick=30000)  # every tick in a window
demo.snapshots(every=64)                          # every 64 ticks
demo.snapshots(seconds=1.0)                        # every second
demo.snapshots(events="player_death")             # at each kill tick
demo.snapshots(every=64, start_tick=29000, end_tick=64000)  # stride, bounded
```

Read a fixed schema of player position, aim, health, weapons, economy, and status.
Use `ticks` for other properties or non-player entities.

One row per active player per tick. Pass any combination of `ticks` (an int or a
list), a stride (`every` / `seconds`), `events` (a name or list), and a
`start_tick` / `end_tick` window — given on their own, the window is a contiguous
range; combined with a sampler, they bound it. At least one must be given.

**Identity, position & movement:** `tick`, `steamid`, `name`, `side`, `x`, `y`, `z`,
`velocity_x`, `velocity_y`, `velocity_z`, `velocity`, `pitch`, `yaw`.

| Column | Type | Description |
| --- | --- | --- |
| `velocity_x` | f32? | X velocity in Hammer units per second. |
| `velocity_y` | f32? | Y velocity in Hammer units per second. |
| `velocity_z` | f32? | Z velocity in Hammer units per second. |
| `velocity` | f32? | Three-dimensional speed derived from the velocity vector. |
| `health` | i32 | Hit points. |
| `armor` | i32 | Armor value. |
| `has_helmet` | bool | Kevlar + helmet. |
| `has_defuser` | bool | Defuse kit. |
| `has_bomb` | bool | Carrying the C4. |
| `active_weapon` | str? | Short name of the weapon currently held. (Per-shot clip / accuracy is on `shots`.) |
| `primary_weapon` | str? | Primary-slot weapon (rifle / SMG / shotgun / sniper / LMG), or null. |
| `secondary_weapon` | str? | Pistol held, or null. |
| `fire_grenades` | i32 | Molotov + incendiary held. |
| `smoke_grenades` | i32 | Smoke grenades held. |
| `he_grenades` | i32 | HE grenades held. |
| `flashbangs` | i32 | Flashbangs held. |
| `decoy_grenades` | i32 | Decoy grenades held. |
| `equipment_value` | i32 | Value of current equipment (`m_unCurrentEquipmentValue`). |
| `equipment_value_round_start` | i32 | Equipment value at the round start. |
| `money` | i32 | Cash on hand. |
| `is_crouched` | bool | Fully ducked. |
| `is_walking` | bool | Moving quietly. |
| `is_jumping` | bool | Airborne (off the ground). |
| `is_in_bomb_zone` | bool | Standing in a plant zone. |
| `is_scoped` | bool | Scoped in. |
| `is_reloading` | bool? | Active weapon's `m_bInReload` value. |
| `is_silent_reloading` | bool? | True when the active weapon's `m_bInReload` and `m_bStealthy` values are both true. |
| `is_defusing` | bool | Defusing the bomb. |
| `is_blinded` | bool | Whether `m_bFlashing` says the player is currently blinded. |
| `flash_duration` | f32 | Replicated duration set at flash onset. This is not a remaining-time counter. |
| `inventory` | str | Comma-separated short names of every weapon in the loadout, in slot order (e.g. `ak47,deagle,knife,flashbang,flashbang,smokegrenade`). |

Reload columns are nullable Boolean columns. Both are `false` when there is
no active weapon. A missing schema field on an active weapon produces `null`.
Older demos without `m_bStealthy` have `null` in `is_silent_reloading` when
a weapon is active. If the schema has a Boolean field but the demo omits its
value, the value defaults to `false`.
The silent-reload column reports stealth reload mode, not measured sound.
The mapping has synthetic tests but has not yet been checked against a
demo that contains quiet reloads.

See {doc}`reference` or `awpy.SNAPSHOT_PROPERTIES` for engine properties.
Snapshot weapon names are short names, such as `ak47` and `usp_silencer`.
Event weapon strings can differ.
Dead players have no weapons but retain their last `equipment_value`.

```python
from awpy import plot

snap = demo.snapshots(ticks=29000)
players = [
    plot.Player(x=r["x"], y=r["y"], z=r["z"], yaw=r["yaw"], hp=r["health"],
                armor=r["armor"], side=r["side"], label=r["name"])
    for r in snap.iter_rows(named=True)
]
fig, ax = plot.frame(demo.header["map_name"], players)
```

Requests for one to four explicit ticks, without other selectors, use seeking.
Other requests decode keyframe segments in parallel.
A coarse stride reduces output, but decoding can still be required between samples.

## Any game event: demo.events

For events without a dedicated dataset, `demo.events` maps event names to
DataFrames — a `tick` column plus one string column per event key. Everything
is parsed lazily and cached.

```python
demo.events.names                    # what the demo contains
demo.events.counts                   # {name: occurrences}
demo.events.bomb_planted             # one event as a DataFrame
demo.events["smokegrenade_detonate"]
```

The {doc}`Reference <reference>` catalogs the common events (also
`awpy.GAME_EVENTS`).

## Per-tick entity state: `ticks`

```python
demo.ticks()                              # default props (below)
demo.ticks(["X", "Y", "Z", "health"])     # friendly aliases
demo.ticks(["m_iHealth", "m_iTeamNum"])   # raw CS2 field names
```

Use `ticks` for a selected set of network properties or for non-player entities.
For example, `demo.ticks(["velocity_x", "velocity_y", "velocity_z", "velocity"])`
returns velocity components and derived speed without the full snapshot schema.

With `players_only=True` (the default) there is **one row per player per tick**,
keyed by `steamid`: each player's pawn and controller are merged into a single
row, and every requested property is read from whichever of the two carries it
(so pawn fields like `health` and controller fields like `name` mix freely).
Columns: `tick`, `steamid`, then one column per requested property, each **typed
natively** — integers → Int64, floats → Float64, booleans → Boolean, strings →
Utf8.

The default `props` are `["X", "Y", "Z", "health", "armor", "team_num"]`.
Use aliases or raw CS2 network names:

| Alias | Meaning |
| --- | --- |
| `X` / `Y` / `Z` | Computed world position (from cell + offset). |
| `health` | `m_iHealth`. |
| `armor` | `m_ArmorValue`. |
| `team_num` | `m_iTeamNum` (2 = T, 3 = CT). |
| `name` | `m_iszPlayerName` (from the controller). |
| `money` | `m_pInGameMoneyServices.m_iAccount`. |
| `velocity_x` / `velocity_y` / `velocity_z` | Networked velocity components. Short aliases `vx` / `vy` / `vz` also work. |
| `velocity` / `speed` | Derived three-dimensional speed. |
| *(anything else)* | Used verbatim as a raw network field name. |

`ticks()` decodes keyframe segments in parallel.

Set `players_only=False` for a raw per-entity dump instead — one row per (tick,
entity), with columns `tick`, `entity_id`, `entity_serial`,
`class_name`, then the requested properties. Use `(entity_id, entity_serial)`
as the stable identity because Source 2 can reuse an entity slot.
