# 📝 Changelog

## 3.0.0 (unreleased)

A full rewrite: a Rust core parser for Counter-Strike 2 (Source 2) demo files
with a Python `Demo` class that returns [Polars](https://pola.rs) DataFrames.

- Combat datasets: `rounds`, `kills`, `damages`, `bomb`, `shots`, `stats`.
- Grenade datasets: `grenades` (trajectories), `fires`, `smokes`, and `blinds`
  (flash events — who was blinded, by whom, and for how long).
- `item_events` — weapon-item transactions (purchases, pickups, and drops),
  reconstructed from inventory state so they work on demos without the
  `item_purchase` event.
- Player datasets: `players` (roster, including each player's team /
  organization name); `snapshots(...)` for per-player state — position,
  velocity (components and 3D speed), health, armor, economy, and loadout — at
  a tick, a list of ticks, a contiguous range
  (`start_tick` / `end_tick`), or sampled across the match by a stride and/or
  event ticks.
- `stats` also reports clutches (`clutches_played`, `clutches_won`, and
  `clutch_1v1` … `clutch_1v5`) and utility (grenade damage, flashes thrown,
  enemies flashed, blind duration dealt); `round_economy` classifies each team's
  buy per round (`pistol` / `eco` / `force` / `full`).
- `kills` flags trades: `is_trade` (this kill avenged a teammate) and
  `victim_traded` (this kill's victim was avenged) — the same classification
  behind `stats.traded_deaths`.
- Metadata: `header`, `tick_rate`, `chat`, `convars`.
- Fixed `Demo.chat`. Awpy now reads user messages that packets store directly
  and messages inside `svc_UserMessage`. It also reads `SayTextChannel`.
- Updated CS2 protobuf definitions to game build `2000899` (source revision
  `10948930`), including the newly required Valve extension definitions; hit
  group names now cover the engine's `unused` (9) and `special` (11) values.
- `awpy.SNAPSHOT_PROPERTIES` and `awpy.GAME_EVENTS` — discoverable catalogs of the
  per-player snapshot features (mapped to engine properties) and common events.
- Generic access: `header`, the `events` mapping, and `ticks()` — one natively
  typed row per player per tick, with default props and friendly aliases
  (`X`/`Y`/`Z`, velocity components and 3D speed, `health`, `armor`,
  `team_num`, `name`, `money`).
- Updated to `pbdems2 0.3`: long-lived player, flash, projectile, and
  inventory tracking now keys entities by slot plus serial, preventing state
  from leaking when Source 2 reuses a slot. Raw `ticks(players_only=False)` rows
  expose `entity_serial` alongside `entity_id`.
- Fast by default: event-based combat datasets now collect their protobuf
  events while decoding entity state, eliminating a separate full event-stream
  traversal. That pass materializes only the legacy event names those datasets
  consume, skips all user messages, and omits unused raw payload copies;
  `ticks` and `snapshots` decode in parallel across keyframes.
- Reduced parser overhead in entity-heavy datasets. Field-key caches now use
  numeric class IDs and do not allocate a class-name string for each lookup.
- Fixed truncated command streams. Message, event, and console-variable scans
  now return a parse error instead of incomplete data.
- Faster cold `stats`: combat events, rounds, and the player roster are now
  collected in one filtered pass. Stats-mode shots retain the identity and side
  needed for clutch reconstruction without decoding active-weapon entities.
  Player and blind tracking process only entities changed on the current tick.
- New `Demo.load(*datasets)` plans, batches, and caches compatible datasets.
  Requested enriched event tables share one decode, as do requested projectile
  tables. Loading `stats` also prepares `rounds`, `players`, `kills`, `damages`,
  and `blinds`, and can fully enrich requested `bomb` / `shots` rows in the same
  fused pass. Ordinary property access retains eager group reuse;
  `Demo.available_datasets()` lists valid names.
- `awpy.plot` for radars, frames, heatmaps, nav meshes, and GIFs (`awpy[plot]`
  extra). `plot.nav` draws a map's walkable areas and can highlight a set of them
  — e.g. a route from `NavMesh.find_path`.
- `awpy.VisibilityChecker` for line-of-sight queries against map meshes, and
  `awpy.NavMesh` for navigation-mesh area lookups and pathfinding.
- `awpy.map_control` — how much of the map each team holds at a tick, by
  `raycast` (line of sight in any direction, smoke-aware), `vision` (the same,
  clipped to each player's field of view — 90° by default, matching CS2), or
  `reachability` (who reaches each area first, molotov-aware);
  `awpy.plot.map_control` shades the radar by controlling side.
- `awpy.data` — map-data cache (mesh / nav / radar assets, versioned releases).
- `awpy` command-line tool; `awpy-dev` developer CLI for parser internals.
