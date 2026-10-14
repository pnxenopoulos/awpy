# Changelog

## 3.0.0

Rust parser for CS2 demos with Python bindings and Polars DataFrames.

- Accept a path or ordered path sequence in `Demo`. Combine multipart stats by
  Steam ID. Keep local ticks with a `part` column. Reject incompatible files,
  missing or overlapping rounds, and splits during live play.
- Return an empty snapshot table when a selected event has no matches.
- Publish wheels for Python 3.11–3.15 on Linux, macOS, and Windows.
  Python 3.15 uses a stable-ABI wheel built with Python 3.14.
- Release Rust and Python packages from manual workflows with a version check.
- Split tests by behavior and share replay fixtures.
- Correct player IDs in combat events. Convert legacy event handles before serial validation.
- Keep dead players' event IDs through validated original-controller handles.
- Count recorded assisters and active flash throwers once each per kill.
- Match each trade kill to the earliest qualifying death within 5.25 seconds.
  Use the same rule for kill flags, traded deaths, and KAST.
- Require Python Polars 2.x. The lockfile now selects `2.0.0`.
  Awpy dataset schemas are unchanged. See the
  [Polars migration guide](https://docs.pola.rs/releases/upgrade/2/) for changes
  to downstream queries, including lazy-query ordering.
- Shortened documentation and corrected cache, chat, and snapshot descriptions.
- Shared developer CLI helpers for file opening, JSON output, row limits,
  and player labels. Removed redundant output buffers and an unused dependency.
- Simplified Python dataset dispatch and shared map-control dataset selection.
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
- Snapshots now include nullable Boolean `is_reloading` and
  `is_silent_reloading` columns from the active weapon. Both are false when
  there is no active weapon. Missing schema fields on an active weapon remain
  null. The silent-reload mapping has synthetic tests; real-demo validation
  is pending.
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
- Updated CS2 protobuf definitions to game build `2000924` (source revision
  `11076591`). The generator uses a bundled compiler and removes unsupported
  C++ annotations from temporary inputs. Upstream files stay unchanged.
- Added the required Valve extension definitions. Hit group names now cover
  the engine's `unused` (9) and `special` (11) values.
- Added an advisory protobuf freshness check to CI. Run
  `./scripts/sync-protos.sh --check` to compare local files with upstream without
  changing them. This check does not block CI Check or releases.
- `awpy.SNAPSHOT_PROPERTIES` and `awpy.GAME_EVENTS` — discoverable catalogs of the
  per-player snapshot features (mapped to engine properties) and common events.
- Generic access: `header`, the `events` mapping, and `ticks()` — one natively
  typed row per player per tick, with default props and friendly aliases
  (`X`/`Y`/`Z`, velocity components and 3D speed, `health`, `armor`,
  `team_num`, `name`, `money`).
- Updated pbdems2 to `0.4.0` for field-path fixes and faster decoding.
- Snapshot queries with two to four explicit ticks now use direct keyframe
  seeks when no other selector is set. These queries return only exact ticks,
  in tick order, without duplicates. Single-tick behavior is unchanged.
- Reduced snapshot memory use. Segment columns stay separate, and plain
  numeric columns use their existing buffers when passed to Polars.
- Added isolated Python API benchmarks with output checks, peak memory,
  runtime samples, and environment metadata.
- Enabled level-one optimization for Awpy and pbdems2 in debug builds to
  reduce local and CI test time. Release settings are unchanged.
- Kept the public names of legacy CS user messages after upstream enum renames.
- Fixed weapon variant names in snapshots and item events. Shared entity
  classes now use the item-definition index, with a subclass-token fallback
  when that index is absent or unknown. This distinguishes Deagle/Revolver,
  M4A4/M4A1-S, and P2000/USP-S. Combat event weapon names are unchanged.
- Player, flash, projectile, and inventory tracking keys entities by slot
  plus serial, preventing state
  from leaking when Source 2 reuses a slot. Raw `ticks(players_only=False)` rows
  expose `entity_serial` alongside `entity_id`.
- Combat datasets collect selected game events during entity decoding.
  This removes a separate event scan and unused payload copies.
  `ticks` and `snapshots` decode keyframe segments in parallel.
- Reduced parser overhead in entity-heavy datasets. Field-key caches now use
  numeric class IDs and do not allocate a class-name string for each lookup.
- Fixed truncated command streams. Message, event, and console-variable scans
  now return a parse error instead of incomplete data.
- Faster cold `stats`: combat events, rounds, and the player roster are now
  collected in one filtered pass. Stats-mode shots retain the identity and side
  needed for clutch reconstruction without decoding active-weapon entities.
  Player and blind tracking process only entities changed on the current tick.
- New `Demo.load(*datasets)` plans, batches, and caches compatible datasets.
  Compatible event and projectile tables share passes. Stats reuse combat,
  round, and roster inputs and can collect requested bomb and shot rows.
  `Demo.available_datasets()` lists valid names.
- Enriched event and projectile datasets now expose each resolved entity's
  create serial with its slot. This identity stays stable when Source 2 reuses a
  slot.
- Snapshots now expose `is_blinded` from `m_bFlashing`. The existing
  `flash_duration` is documented as the replicated onset duration, not a
  remaining-time counter. Map control uses both values and no longer treats a
  stale duration as an active blind.
- Event-based snapshot selection decodes only the requested legacy event names
  instead of materializing the complete event stream. Projectile tracking also
  caches invariant thrower data.
- `Demo.player_stats()` reuses decoded inputs and caches both knife-round
  variants. Calling the default form after `demo.stats` no longer parses the
  demo again.
- Steam ID columns now have an explicit `UInt64` type, including empty and
  all-null columns. This prevents accidental floating-point conversion inside
  Awpy datasets.
- Added `tick_to_seconds()` and `seconds_to_tick()` conversion helpers.
- `awpy.plot` for radars, frames, heatmaps, nav meshes, and GIFs (`awpy[plot]`
  extra). `plot.nav` draws a map's walkable areas and can highlight a set of them
  — e.g. a route from `NavMesh.find_path`.
- `awpy.VisibilityChecker` for line-of-sight queries against map meshes, and
  `awpy.NavMesh` for navigation-mesh area lookups and pathfinding.
- `awpy.map_control` estimates control with `raycast`, `vision`, or
  `reachability`;
  `awpy.plot.map_control` shades the radar by controlling side.
- `awpy.data` — map-data cache (mesh / nav / radar assets, versioned releases).
- `awpy` command-line tool; `awpy-dev` developer CLI for parser internals.
