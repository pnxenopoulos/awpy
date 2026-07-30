# 📊 Datasets

Awpy's headline datasets are properties on `Demo` — Polars DataFrames with
typed columns, computed on first access and cached.

## `rounds`

```python
demo.rounds
```

One row per round, reconstructed from the `CCSGameRules` entity state. Because
it relies on game-rules state rather than `round_start` / `round_end` game
events (which many competitive CS2 demos omit), it works across demos — and it
correctly includes the overtime-deciding round, which coincides with the "game
over" broadcast.

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

One row per `player_death` game event, with each participant **resolved** to a
real player: the attacker, victim, and assister each get a Steam id, name, side,
and world position `(x, y, z)` at the kill tick. This performs a full entity
decode (of the player pawns and controllers), so it is slower than the
event-only datasets.

For each of `attacker`, `victim`, `assister`:

| Column | Type | Description |
| --- | --- | --- |
| `<who>_steamid` | u64? | 64-bit Steam id (from the controller's `m_steamID`). |
| `<who>_name` | str? | Display name (`m_iszPlayerName`). |
| `<who>_side` | str? | `terrorist` / `counter-terrorist`. |
| `<who>_x` / `_y` / `_z` | f32? | World position (Hammer units) at the kill tick. |

Plus the kill's own fields: `weapon` (str), `headshot` (bool), `dominated`,
`noscope` (bool), `penetrated`, `revenge`, `thrusmoke` (bool), `hitgroup`,
`hitgroup_name`, `is_trade` (bool), `victim_traded` (bool), and `tick`.

Participant columns are **null** when that participant is absent (no assister)
or can't be resolved (e.g. a world kill).

### Trades

Two flags mark each kill's place in a trade. A **trade** is a kill that avenges a
teammate killed within the last 5 seconds:

| Column | Description |
| --- | --- |
| `is_trade` | This kill **is** a trade — the attacker killed someone who had just killed one of their teammates. |
| `victim_traded` | This kill's **victim was traded** — a teammate of the victim killed this attacker within the window. |

The two are duals: the kill that avenges a death carries `is_trade`, and the death
it avenged carries `victim_traded`. `victim_traded` is what the `stats` dataset
counts as `traded_deaths` — both come from one classifier, so they cannot
disagree. Note that the totals differ: one kill can avenge several teammates at
once (kill two enemies, get killed by a third, and both of those deaths are
traded), so `victim_traded` is usually the more common of the two. A kill can also
carry both flags — a trade that was itself traded back.

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

For each of `attacker`, `victim`: `<who>_steamid`, `<who>_name`, `<who>_side`,
`<who>_x` / `_y` / `_z`. Plus: `weapon`, `dmg_health`, `dmg_armor`, `hitgroup`,
`hitgroup_name`, `health_pre` / `health_post`, `armor_pre` / `armor_post`, and
`tick`. Pre-values are reconstructed as `post + damage`, clamped to the 100 HP /
armor cap — CS2 reports raw damage, so a lethal hit's `dmg_health` can exceed the
victim's health (e.g. an AWP for 115), which would otherwise imply >100 pre-HP.

## `bomb`

```python
demo.bomb
```

Bomb actions with the acting player and their position. Columns: `tick`,
`event` (one of `pickup`, `drop`, `start_plant`, `interrupt_plant`,
`finish_plant`, `defuse`), `steamid`, `name`, `bombsite` (`A` / `B`, from the
planted C4; null before the plant), `x`, `y`, `z`.

Some demos don't emit the begin/abort-plant events, so `start_plant` /
`interrupt_plant` rows may be absent.

## `grenades`

```python
demo.grenades
```

Thrown-grenade **trajectories** — one row per tick each grenade projectile is in
flight (samples stop once it settles). Columns: `tick`, `thrower_name`,
`thrower_steamid`, `thrower_side`, `type` (`smoke` / `he` / `flashbang` /
`molotov` / `decoy`), `entity_id`, `x`, `y`, `z`.

## `fires` / `smokes`

```python
demo.fires    # burning infernos (molotov / incendiary)
demo.smokes   # deployed smoke clouds
```

**One row per fire / smoke.** Columns: `start_tick`, `end_tick`,
`thrower_name`, `thrower_steamid`, `thrower_side`, `entity_id`, `x`, `y`, `z`
(`fires` also has a `type` column). An inferno or smoke sits at a fixed
position, so a single row with its `[start_tick, end_tick]` window fully
describes it.

The window is the game's own event pair, not the (longer) entity lifetime:
`inferno_startburn` → `inferno_expire` for fires (the ~7 s burn, cut short when a
molotov is smoked out) and `smokegrenade_detonate` → `smokegrenade_expired` for
smokes (the deployed cloud, excluding the throw).

To find which players stood in a fire, interval-join positions against the
`[start_tick, end_tick]` window rather than an equijoin on tick:

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
state. Columns: `tick`, `steamid`, `name`, `side`, `x`, `y`, `z`, `pitch`,
`yaw`, `weapon`, `scoped`, `inaccuracy` (the weapon's networked accuracy
penalty), `num_bullets_remaining` (active weapon's clip). Reading the active
weapon requires a full entity pass, so this is the slowest dataset.

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
| `victim_steamid` / `_name` / `_side` / `_x` / `_y` / `_z` | | The blinded player. |
| `duration` | f32 | Blind duration in seconds. |

The attacker may be a teammate (a team-flash) or the victim themselves (a
self-flash), so filter on `attacker_side` / `victim_side` or compare Steam ids
as needed.

CS2 **GOTV demos usually omit the `player_blind` game event** (as they omit chat
and round events), so awpy reconstructs blinds from entity state instead — a
rising edge of a pawn's networked flash duration, attributed to the
`flashbang_detonate` on the same tick. This works on every demo; the only
requirement is that the demo carries `flashbang_detonate` (an empty frame is
returned if it doesn't).

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
| `steamid` / `name` / `side` | | The acting player. |
| `item` | str | Short weapon name (e.g. `ak47`, `deagle`, `hegrenade`). |
| `x` / `y` / `z` | f32? | The player's world position. |
| `original_owner_steamid` | u64? | Steam id of the weapon's original owner. For a `pickup`, whose weapon it originally was; equals `steamid` for a `purchase`. |
| `cost` | i32? | Money spent, for a `purchase` (null otherwise). May bundle other buys made on the same tick. |
| `near_buy_zone` | bool? | For a `drop`, whether it was dropped near a buy zone (e.g. dropping a weapon for a teammate); null otherwise. |

Like `blinds`, this is **reconstructed from entity state** rather than events,
because CS2 GOTV/broadcast demos omit the `item_purchase` event. Each player's
inventory (`m_hMyWeapons`) is tracked over time: a weapon entering it is an
acquisition — a **purchase** if the player's money drops that tick, otherwise a
**pickup** — and a weapon left on the ground is a **drop**. Thrown grenades
(which are *used*, not dropped) are excluded, as is the knife and free default
loadout equipment.

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

Precise definitions of every metric — assists and flash assists, opening
kills / deaths, **traded deaths**, **clutches**, KAST, ADR, multi-kills, and the
utility stats — are in the {doc}`Reference <reference>`. In brief: **KAST** is the
share of rounds where the player got a **K**ill, **A**ssist, **S**urvived, or was
**T**raded (their death was avenged by a teammate within 5 s), and **ADR** is
average damage per round counting the actual HP removed from enemies.

Every player is treated as having played every round (the denominator for KAST
and ADR is the match's round count), so players who join or leave mid-match are
approximate.

**Knife rounds are excluded by default.** A knife round (a side-decider round of
all-melee kills — see `is_knife_round` on the `rounds` dataset) doesn't count
toward the score, so its kills, deaths, assists, and damage are dropped and it's
removed from every denominator, matching competitive scoreboards. To count them
instead, use the method form and pass the flag:

```python
demo.stats                                    # excludes knife rounds (default)
demo.player_stats(include_knife_rounds=True)  # counts them
```

**`stats` is cached; `player_stats()` is not.** `demo.stats` is a property
computed once (alongside the other datasets) and returned instantly on every
later access. `demo.player_stats(...)` is a method that **recomputes on every
call** — it re-runs the kill/damage entity pass and the aggregation and caches
nothing, so on a large demo it costs a few seconds *each time*. Reach for the
method only when you need the `include_knife_rounds` toggle, and keep the
returned DataFrame if you use it more than once rather than calling it in a loop.

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

One row per (round, side): a team's total equipment value once the buy is locked
(read at freeze end) and its buy-type classification. Columns: `round_num`,
`side`, `equipment_value`, `buy_type`, `n_players`. `buy_type` is `pistol` / `eco`
/ `force` / `full` — see the {doc}`Reference <reference>` for the thresholds and
how pistol rounds are detected. (This is the *current* equipment at freeze end —
the finished buy; the `equipment_value_round_start` snapshot column is the pre-buy
carry-over.) Knife rounds are excluded.

```python
# Rounds a team full-bought but lost
demo.round_economy.filter(pl.col("buy_type") == "full")
```

## `players`

```python
demo.players  # steamid, name, side, team_clan_name
```

The roster: one row per player seen in the demo. `side` is the last team the
player was observed on (players swap at halftime); bots (e.g. the GOTV camera
controller) have `steamid` 0.

`team_clan_name` is the organization the player's team was playing under — e.g.
`"Imperial"` — read from the `CCSTeam` entities. Tournament and league servers set
it; casual matchmaking leaves it empty, in which case the column is null. Because
it is captured at the same moment as `side`, a player who leaves mid-match keeps
the team they actually played for rather than whoever held their side afterwards.

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

Chat messages, decoded from `SayText` / `SayText2` user messages. `channel`
distinguishes all-chat from team chat (`Cstrike_Chat_All`, `Cstrike_Chat_T`,
`Cstrike_Chat_CT`, ...). Note that server-side (GOTV) recordings may strip
chat entirely — an empty frame with this schema is normal for some demos.

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

**This is the way to read player state** for analysis and plotting: a fixed,
curated schema — position, aim, health, weapons, economy, and status for every
player, with resolved side and weapon names — that drops straight into
{doc}`plot <plot>`. For anything it doesn't cover — a raw or derived network
property, non-player entities, or a leaner slice of columns over every tick —
drop down to the raw `ticks` reader (below).

One row per active player per tick. Pass any combination of `ticks` (an int or a
list), a stride (`every` / `seconds`), `events` (a name or list), and a
`start_tick` / `end_tick` window — given on their own, the window is a contiguous
range; combined with a sampler, they bound it. At least one must be given.

**Identity & position:** `tick`, `steamid`, `name`, `side`, `x`, `y`, `z`,
`pitch`, `yaw`.

| Column | Type | Description |
| --- | --- | --- |
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
| `is_defusing` | bool | Defusing the bomb. |
| `flash_duration` | f32 | Seconds of blindness remaining (0 if not blinded). |
| `inventory` | str | Comma-separated short names of every weapon in the loadout, in slot order (e.g. `ak47,deagle,knife,flashbang,flashbang,smokegrenade`). |

Each column and the CS2 engine property it comes from is listed in the
{doc}`Reference <reference>` (also `awpy.SNAPSHOT_PROPERTIES`). Weapon names match
the `weapon` field of `kills` / `shots` (e.g. `ak47`, `awp`,
`usp_silencer`). Dead players report no weapons (they drop on death) but retain
their last `equipment_value`. Rows feed straight into {doc}`plot <plot>`:

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

A single `ticks` value seeks directly to that tick (fast anywhere in the demo);
every other form decodes in parallel across keyframe segments — the cost is the
decode, not the (usually small) sampled output, so a coarse stride over a big demo
is cheap.

## Any game event: `demo.events`

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

The **raw, low-level reader** — the escape hatch beneath `snapshots` (above).
For curated player state, prefer `snapshots`; reach for `ticks` when you need one
of the things its fixed schema can't give you:

- **A raw or derived network property** `snapshots` doesn't ship — e.g.
  `demo.ticks(["m_vecVelocity[0]", "m_vecVelocity[1]"])` for velocity. Any CS2
  field is fair game, by friendly alias or raw name.
- **Non-player entities**, via `players_only=False` — projectiles, the planted
  C4, hostages, and every other entity, not just players.
- **A lean slice over every tick** — request only the columns you need (e.g.
  just `X`/`Y`/`Z`) instead of the full ~30-column snapshot, which is markedly
  faster and lighter when you're pulling the whole match (e.g. movement or
  heatmap features across a corpus).

With `players_only=True` (the default) there is **one row per player per tick**,
keyed by `steamid`: each player's pawn and controller are merged into a single
row, and every requested property is read from whichever of the two carries it
(so pawn fields like `health` and controller fields like `name` mix freely).
Columns: `tick`, `steamid`, then one column per requested property, each **typed
natively** — integers → Int64, floats → Float64, booleans → Boolean, strings →
Utf8.

Omitting `props` uses a sensible default: `["X", "Y", "Z", "health", "armor",
"team_num"]`. Property names accept friendly aliases as well as raw CS2 network
names:

| Alias | Meaning |
| --- | --- |
| `X` / `Y` / `Z` | Computed world position (from cell + offset). |
| `health` | `m_iHealth`. |
| `armor` | `m_ArmorValue`. |
| `team_num` | `m_iTeamNum` (2 = T, 3 = CT). |
| `name` | `m_iszPlayerName` (from the controller). |
| `money` | `m_pInGameMoneyServices.m_iAccount`. |
| *(anything else)* | Used verbatim as a raw network field name. |

`ticks()` decodes the demo in parallel across keyframe segments, so it is fast
even over a full match.

Set `players_only=False` for a raw per-entity dump instead — one row per (tick,
entity), with columns `tick`, `entity_id`, `class_name`, then the requested
properties.
