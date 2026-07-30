# Reference

Three lookups: the per-player **properties**, the game **events**, and how the
derived numbers (buy types, ADR, KAST, trades, …) are **defined**.

## Player properties

The per-player features returned by {meth}`Demo.snapshot` / {meth}`Demo.snapshots`,
each mapped to the CS2 network property it is read from. Available
programmatically as `awpy.SNAPSHOT_PROPERTIES`.

The scalar fields can also be requested in {meth}`Demo.ticks` — by these readable
names (the aliases `x`/`y`/`z`, `health`, `armor`, `team_num`, `name`, `money`) or
by any raw network name (`m_iHealth`, `m_bIsScoped`, …).

### Identity & position

| Property | Engine field |
| --- | --- |
| `steamid` | `m_steamID` |
| `name` | `m_iszPlayerName` |
| `side` | `m_iTeamNum` (2 = terrorist, 3 = counter-terrorist) |
| `x` / `y` / `z` | `CBodyComponent…m_cell{X,Y,Z}` + `m_vec{X,Y,Z}` (computed world position) |
| `pitch` / `yaw` | `m_angEyeAngles` |

### Health & equipment

| Property | Engine field |
| --- | --- |
| `health` | `m_iHealth` |
| `armor` | `m_ArmorValue` |
| `has_helmet` | `m_pItemServices.m_bHasHelmet` |
| `has_defuser` | `m_pItemServices.m_bHasDefuser` |
| `has_bomb` | holds a `CC4` in `m_pWeaponServices.m_hMyWeapons` |

### Weapons & utility held

| Property | Engine field |
| --- | --- |
| `active_weapon` | `m_pWeaponServices.m_hActiveWeapon` |
| `primary_weapon` | `m_pWeaponServices.m_hMyWeapons` (primary slot) |
| `secondary_weapon` | `m_pWeaponServices.m_hMyWeapons` (pistol slot) |
| `fire_grenades` / `smoke_grenades` / `he_grenades` / `flashbangs` / `decoy_grenades` | counts from `m_pWeaponServices.m_hMyWeapons` |
| `inventory` | full loadout (slot order) from `m_pWeaponServices.m_hMyWeapons` |

### Economy

| Property | Engine field |
| --- | --- |
| `equipment_value` | `m_unCurrentEquipmentValue` (current) |
| `equipment_value_round_start` | `m_unRoundStartEquipmentValue` (pre-buy carry-over) |
| `money` | `m_pInGameMoneyServices.m_iAccount` |

### Status

| Property | Engine field |
| --- | --- |
| `is_crouched` | `m_pMovementServices.m_bDucked` |
| `is_walking` | `m_bIsWalking` |
| `is_jumping` | `m_fFlags` with `FL_ONGROUND` clear (airborne) |
| `is_in_bomb_zone` | `m_bInBombZone` |
| `is_scoped` | `m_bIsScoped` |
| `is_defusing` | `m_bIsDefusing` |
| `flash_duration` | `m_flFlashDuration` (seconds of blindness remaining) |

## Game events

Common CS2 game events. The events actually present in a demo are
`demo.events.names` (and `demo.events.counts`); `demo.events[name]` returns any of
them as a DataFrame. This catalog is available programmatically as
`awpy.GAME_EVENTS`.

| Event | Description |
| --- | --- |
| `round_start` | A round begins. |
| `round_freeze_end` | Freeze time ends; players can move. |
| `round_end` | A round is decided (carries winner + reason). |
| `round_officially_ended` | The round is fully wrapped up (post-round). |
| `begin_new_match` | A new match starts. |
| `announce_phase_end` | A phase (e.g. the first half) ends. |
| `player_death` | A player is killed (attacker, victim, assister, weapon). |
| `player_hurt` | A player takes damage (health / armor before & after). |
| `player_blind` | A player is blinded by a flashbang. |
| `player_team` | A player joins or switches team (fires for everyone at halftime). |
| `player_spawn` / `player_connect_full` / `player_disconnect` | Spawn / connect / disconnect. |
| `player_footstep` / `player_jump` / `player_ping` | Footstep / jump / map ping. |
| `weapon_fire` | A weapon is fired (or a grenade thrown). |
| `weapon_reload` / `weapon_zoom` | Reload / scope zoom. |
| `item_pickup` / `item_purchase` / `item_equip` | Pick up / buy / equip an item. |
| `bomb_beginplant` / `bomb_planted` | Start planting / bomb planted. |
| `bomb_begindefuse` / `bomb_defused` | Start defusing / bomb defused. |
| `bomb_exploded` / `bomb_dropped` / `bomb_pickup` | Explode / drop / pick up. |
| `flashbang_detonate` / `hegrenade_detonate` | Flash / HE detonation. |
| `smokegrenade_detonate` / `smokegrenade_expired` | Smoke starts / dissipates. |
| `decoy_started` / `decoy_detonate` | Decoy start / finish. |
| `inferno_startburn` / `inferno_expire` | Molotov / incendiary fire starts / burns out. |

## Definitions

How the reconstructed and aggregated numbers are computed.

### Sides & teams

`side` is `"terrorist"` / `"counter-terrorist"`, from the player's `m_iTeamNum`
(2 / 3). Players swap sides at halftime, so a player's `side` changes across the
match; the persistent identity is `steamid`.

A player's **team** — the organization they play for — is separate and does *not*
swap: `demo.players` reports it as `team_clan_name` (e.g. `"Imperial"`), from the
`CCSTeam` entities' `m_szClanTeamname`. Tournament and league servers set it;
casual matchmaking leaves it null.

### Ticks & time

Demo timings are in **ticks**. `demo.tick_rate` gives ticks per second, computed
from the demo's own playback timing (`playback_ticks / playback_time`) and falling
back to `64.0` when the demo does not report it. Competitive CS2 demos are 64 tick;
some are recorded at 128.

```python
round_seconds = (row["end_tick"] - row["freeze_end_tick"]) / demo.tick_rate
```

### Buy types (`round_economy`)

Each team's buy per round, from its **total equipment value at freeze end** (the
finished buy — not `equipment_value_round_start`, which is the pre-buy carry-over):

- **`pistol`** — round 1, and the first round after the halftime side switch.
  Detected from the switch itself (a majority of players change side between
  consecutive rounds), so it holds for any match format; overtime's later
  switches are classified by value, not as pistols.
- **`eco`** — team equipment value < $5,000 (saving).
- **`force`** — $5,000 – $20,000 (a partial / force buy).
- **`full`** — ≥ $20,000.

Knife rounds are excluded.

### Player stats (`stats`)

One row per player, over the match. Knife rounds are excluded by default (pass
`include_knife_rounds=True` to {meth}`Demo.player_stats` to keep them). Every
player is treated as having played every round, so KAST / ADR denominators are the
match's round count and players who join or leave mid-match are approximate.

- **Kills / deaths** — enemy kills (suicides and team kills excluded) and deaths.
- **Assists** — the game's attribution: dealing the victim ≥ 40 HP **or** blinding
  them (a *flash assist*) before a teammate got the kill. Only ever credited
  against opponents.
- **Flash assists** (`flash_assists`) — the subset of assists that came from a
  flashbang, so `flash_assists ≤ assists`. (Third-party sites often compute a
  different flash-assist figure from flash→kill correlation; the two are not
  directly comparable.)
- **Headshot %** (`headshot_pct`) — `headshot_kills / kills × 100` (0 with no
  kills).
- **Opening kill / death** — the attacker / victim of the **first** kill of a
  round.
- **Traded death** — a death that was avenged: the player who killed you is
  themselves killed by one of **your** teammates within the **trade window** (5
  seconds by default). This is what the *T* in KAST rewards — you count for the
  round even though you died, because your death was traded back. The `kills`
  dataset exposes the same classification per kill as `victim_traded`, and the
  avenging kill as `is_trade`.
- **KAST** — the percentage of rounds in which the player got a **K**ill, an
  **A**ssist, **S**urvived (was not killed), or was **T**raded.
- **ADR** — average damage per round, using the **actual HP removed** from
  enemies: each hit is capped at the victim's remaining health and chained across
  the round, so a killing blow counts only what the victim had left (an AWP that
  "does 115" to a 40 HP enemy removes 40, not 115). Team, self, and world (e.g.
  fall) damage are excluded.
- **Multi-kill rounds** (`multikill_2k` … `multikill_5k`) — rounds with exactly
  2 / 3 / 4 / 5-or-more kills.

#### Clutches

A **clutch** is a round the player was left to finish alone: they became the last
player alive on their side while at least one opponent was still up.

- **`clutches_played`** — how many such situations the player was in.
- **`clutches_won`** — how many of those rounds their side went on to win.
- **`clutch_1v1` … `clutch_1v5`** — clutches **won**, bucketed by how many
  opponents were alive at the moment the player was left alone. Losses are counted
  in `clutches_played` only, so `clutch_1v1 + … + clutch_1v5 == clutches_won`.

Two details worth knowing:

- The situation is **fixed at the moment the player is left alone**. A 1v3 stays a
  1v3 in `clutch_1v3` even if two of the three die to a teammate's grenade
  afterwards — it is not re-graded as a 1v1.
- The player must *become* last alive. A side that fields a single player for the
  whole round (after a disconnect, say) never registers a clutch, because there was
  no transition.

Alive / dead state is reconstructed from the event datasets rather than from
per-tick entity state, so each side's roster for a round is inferred from who
appears in that round's events — carried across rounds a player was quiet in, and
re-derived after each side swap. Players who join or leave mid-match are covered
only for the rounds they actually appear in.

#### Utility

- **`utility_damage`** — grenade damage dealt to enemies (HE + molotov /
  incendiary), as actual HP removed (chained like ADR).
- **`flashes_thrown`** — flashbangs the player threw.
- **`enemies_flashed`** — times an enemy was blinded by one of the player's
  flashes (team-flashes and self-flashes are not counted).
- **`flash_duration_dealt`** — total seconds of blindness inflicted on enemies.

### Positions

All coordinates are world coordinates in **Hammer units**, Z-up — the same frame
used by {doc}`nav <nav>` and {doc}`visibility <visibility>`, so entity positions
can be passed straight in.
