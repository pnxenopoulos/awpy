# Reference

Snapshot properties, game events, and metric definitions.

## Player properties

{meth}`Demo.snapshots` returns the properties below.
The mapping is also available as `awpy.SNAPSHOT_PROPERTIES`.
Use {meth}`Demo.ticks` for supported aliases or raw network fields.

### Identity & position

| Property | Engine field |
| --- | --- |
| `steamid` | `m_steamID` |
| `name` | `m_iszPlayerName` |
| `side` | `m_iTeamNum` (2 = terrorist, 3 = counter-terrorist) |
| `x` / `y` / `z` | `CBodyComponent…m_cell{X,Y,Z}` + `m_vec{X,Y,Z}` (computed world position) |
| `pitch` / `yaw` | `m_angEyeAngles` |
| `velocity_x` / `velocity_y` / `velocity_z` | `m_vecVelocity` components |
| `velocity` | Three-dimensional speed from the velocity components |

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
| `is_reloading` | Active weapon: `m_bInReload` |
| `is_silent_reloading` | Active weapon: `m_bInReload && m_bStealthy` |
| `is_defusing` | `m_bIsDefusing` |
| `is_blinded` | `m_bFlashing` |
| `flash_duration` | `m_flFlashDuration` (onset duration, not remaining time) |

Reload properties come from the active weapon.
Both are false without an active weapon and null if a required schema field is missing.
Omitted Boolean values default to false when the field exists.
Quiet reloads have synthetic tests but no demo-backed validation.

## Game events

Use `demo.events.names` and `demo.events.counts` to inspect a demo.
Use `demo.events[name]` to read an event DataFrame.
This catalog is also available as `awpy.GAME_EVENTS`.

| Event | Description |
| --- | --- |
| `round_start` | A round begins. |
| `round_freeze_end` | Freeze time ends; players can move. |
| `round_end` | A round is decided (carries winner + reason). |
| `round_officially_ended` | The post-round period ends. |
| `begin_new_match` | A new match starts. |
| `announce_phase_end` | A phase (e.g. the first half) ends. |
| `player_death` | A player is killed (attacker, victim, assister, weapon). |
| `player_hurt` | A player takes damage (damage and remaining health / armor). |
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
- **Assists** — the game's recorded assister, plus teammates whose enemy blind
  is still active at the kill. Each player receives at most one assist per kill.
  The killer cannot also receive an assist.
- **Flash assists** (`flash_assists`) — recorded flash assists and active blind
  matches. These are a subset of assists. Several players can assist one kill.
  Blind matches must use the same round and victim pawn (when its ID and serial
  are available). Timing uses the demo's tick rate.
- **Headshot %** (`headshot_pct`) — `headshot_kills / kills × 100` (0 with no
  kills).
- **Opening kill / death** — the attacker / victim of the **first** kill of a
  round.
- **Traded death** — each revenge kill trades only the earliest qualifying
  teammate death within 5.25 seconds. Each death can be traded once.
  The matched death has `victim_traded` in `kills`; the revenge kill has `is_trade`.
- **KAST** — the percentage of rounds in which the player got a **K**ill, an
  **A**ssist, **S**urvived (was not killed), or was **T**raded.
- **ADR** — recorded enemy damage per round. Each hit uses `dmg_health`, capped
  at the victim's previous `health_post` (100 for the first hit in a round).
  All hits update that health, including hits in the same tick.
  Team, self, and world damage are excluded. Health rounding adds no damage.
- **Multi-kill rounds** (`multikill_2k` … `multikill_5k`) — rounds with exactly
  2 / 3 / 4 / 5-or-more kills.

#### Clutches

A clutch starts when a player becomes the last survivor on their side
with at least one living opponent.

- **`clutches_played`** — how many such situations the player was in.
- **`clutches_won`** — how many of those rounds their side went on to win.
- **`clutch_1v1` … `clutch_1v5`** — clutches **won**, bucketed by how many
  opponents were alive at the moment the player was left alone. Losses are counted
  in `clutches_played` only, so `clutch_1v1 + … + clutch_1v5 == clutches_won`.

The opponent count is fixed when the clutch starts.
Later deaths do not change a 1v3 to a 1v1.
A side with one player for the complete round does not register a clutch:
the player must become the last survivor.

Alive / dead state is reconstructed from the event datasets rather than from
per-tick entity state, so each side's roster for a round is inferred from who
appears in that round's events — carried across rounds a player was quiet in, and
re-derived after each side swap. Players who join or leave mid-match are covered
only for the rounds they actually appear in.

#### Utility

- **`utility_damage`** — grenade damage dealt to enemies (HE + molotov /
  incendiary), capped by the same rule as ADR.
- **`flashes_thrown`** — flashbangs the player threw.
- **`enemies_flashed`** — times an enemy was blinded by one of the player's
  flashes (team-flashes and self-flashes are not counted).
- **`flash_duration_dealt`** — total seconds of blindness inflicted on enemies.

### Positions

Positions use Hammer units, with Z as the vertical axis.
The {doc}`nav` and {doc}`visibility` APIs use the same coordinates.
