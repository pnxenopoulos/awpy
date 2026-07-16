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
- Player datasets: `players` (roster); `snapshots(...)` for per-player state —
  position, health, armor, economy, and loadout — at a tick, a list of ticks, a
  contiguous range (`start_tick` / `end_tick`), or sampled across the match by a
  stride and/or event ticks.
- `stats` also reports utility (grenade damage, flashes thrown, enemies flashed,
  blind duration dealt); `round_economy` classifies each team's buy per round
  (`eco` / `force` / `full`).
- Metadata: `chat`, `convars`.
- `awpy.SNAPSHOT_PROPERTIES` and `awpy.GAME_EVENTS` — discoverable catalogs of the
  per-player snapshot features (mapped to engine properties) and common events.
- Generic access: `header`, the `events` mapping, and `ticks()` — one natively
  typed row per player per tick, with default props and friendly aliases
  (`X`/`Y`/`Z`, `health`, `armor`, `team_num`, `name`, `money`).
- Fast by default: the headline datasets decode together in one parallel pass on
  first access; `ticks` and `snapshots` decode in parallel across keyframes.
- `awpy.plot` for radars, frames, heatmaps, and GIFs (`awpy[plot]` extra).
- `awpy.VisibilityChecker` for line-of-sight queries against map meshes, and
  `awpy.NavMesh` for navigation-mesh area lookups and pathfinding.
- `awpy.data` — map-data cache (mesh / nav / radar assets, versioned releases).
- `awpy` command-line tool; `awpy-dev` developer CLI for parser internals.
