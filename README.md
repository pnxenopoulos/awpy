<div align="center">

# Awpy

<p>
  <a href="https://discord.gg/W34XjsSs2H"><img src="https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord&logoColor=white&style=for-the-badge" alt="Awpy Discord"></a>
  <a href="https://awpy.readthedocs.io"><img src="https://readthedocs.org/projects/awpy/badge/?version=latest&style=for-the-badge" alt="Docs"></a>
  <a href="https://github.com/pnxenopoulos/awpy/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/pnxenopoulos/awpy/ci.yml?style=for-the-badge" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge" alt="License: MIT"></a>
</p>

<p>
  <a href="https://pypi.org/project/awpy/"><img src="https://img.shields.io/pypi/v/awpy.svg?style=for-the-badge" alt="PyPI"></a>
  <a href="https://pepy.tech/project/awpy"><img src="https://img.shields.io/pepy/dt/awpy?style=for-the-badge" alt="Downloads"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/pypi/pyversions/awpy?style=for-the-badge" alt="Python 3.11+"></a>
</p>

</div>

Awpy is a fast [Counter-Strike 2](https://www.counter-strike.net/cs2) demo (`.dem`) parser written in Rust with native Python bindings. It reads Source 2 demo files and returns [Polars](https://pola.rs) DataFrames, giving you structured access to match data without touching the binary format or parsing code yourself.

CS2 runs on the Source 2 engine, so Awpy shares its core with [Boon](https://github.com/pnxenopoulos/boon), a Deadlock parser: the `PBDEMS2` container, bit-level wire encodings, flattened serializers, the entity system, and string tables are all Source 2 mechanisms. Awpy adapts the game-specific parts — the CS2 protobufs, a handful of CS2 field decoders, and the CS2 name tables (teams, hit groups, round-end reasons, game phases).

## Table of Contents

- [Why Awpy?](#why-awpy)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Available Datasets](#available-datasets)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Development](#development)
- [License](#license)

## Why Awpy?

CS2 demo files hold a wealth of match data — player positions, kills, damage, round outcomes, grenades, and more — but the Source 2 demo format is complex and undocumented. Awpy handles the low-level parsing so you can focus on analysis.

- ⚡ **Fast.** The core parser is written in Rust. A full match parses in seconds, not minutes.
- 📊 **Structured output.** Every dataset is a Polars DataFrame, ready for filtering, grouping, joins, and visualization.
- 🎯 **Parse only what you need.** Ask for one event or a handful of entity properties and Awpy skips the rest.
- 🔫 **CS2-aware.** Rounds are reconstructed from game-rules state (so they work even on demos without `round_start` / `round_end` events); kills and damage carry every field; hit groups and round-end reasons are decoded to names.
- 🗂️ **Comprehensive.** Rounds, kills, damage, bomb events, grenade trajectories, infernos, smokes, shots, flashes, item buys/pickups/drops, and a per-player scoreboard (KAST, ADR, openings, trades) — each one property access.
- 💻 **CLI included.** A standalone command-line tool for quick inspection without writing any code.

## Installation

Awpy can be used as a Python library, a Rust crate, or a standalone CLI tool.

### Python

We recommend using [uv](https://docs.astral.sh/uv/):

```bash
uv add awpy
```

You can also use pip:

```bash
pip install awpy
```

Awpy ships as a pre-built wheel with a Rust backend — no compiler required. Requires Python 3.11+.

### CLI

Installing the Python package also installs the `awpy` command for demo
inspection and map-data management:

```bash
awpy info match.dem
awpy kills match.dem --limit 20
awpy stats match.dem --json
awpy get              # download the latest map-data release
```

(For parser-internals debugging there is also a Rust developer binary,
`awpy-dev`: `cargo install --path crates/awpy-dev`.)

### Rust library

The crates aren't published to crates.io yet — use a git dependency:

```toml
[dependencies]
awpy = { git = "https://github.com/pnxenopoulos/awpy" }
```

## Quick Start

### Python

```python
from awpy import Demo

demo = Demo("match.dem")

# File header + playback info
print(demo.header["map_name"])   # "de_inferno"

# Structured datasets, one call each — all Polars DataFrames
rounds = demo.rounds           # one row per round, winner + reason
kills = demo.kills             # every player_death, participants resolved
damages = demo.damages         # every player_hurt, health/armor pre + post
stats = demo.stats             # per-player scoreboard (KAST, ADR, ...)

# Any game event, long-form (demo.events.names lists them)
pings = demo.events.player_ping

# Game state at a moment, or sampled across the match
snap = demo.snapshots(ticks=29000)             # every player's state at one tick
series = demo.snapshots(every=64)       # one sample per 64 ticks

# Per-tick player state — one row per player per tick, decoded in parallel
ticks = demo.ticks()                    # default: X, Y, Z, health, armor, team_num
ticks = demo.ticks(["health", "m_iTeamNum"])

# Round wins by side
demo.rounds.group_by("winner_side").len()
```

### CLI

```bash
# File header and playback info
awpy info match.dem

# Per-round table (winner, reason, timings)
awpy rounds match.dem

# Kills, with players resolved
awpy kills match.dem --limit 20

# Game events (--summary for counts, a name to dump one event)
awpy events match.dem --summary
awpy events match.dem player_ping --json

# All available commands
awpy --help
```

### Rust

```rust
use std::path::Path;
use awpy::Parser;

let parser = Parser::from_file(Path::new("match.dem"))?;
println!("map: {:?}", parser.file_header()?.map_name);

// Game events
for event in parser.events(None)? {
    if event.name == "player_death" {
        println!("[{}] {:?}", event.tick, event.keys);
    }
}

// Entities, tick by tick
parser.run_to_end(|ctx| {
    for (_, entity) in ctx.entities.iter() {
        if entity.active && entity.class_name == "CCSPlayerPawn" {
            // read entity fields
        }
    }
})?;
# Ok::<(), awpy::Error>(())
```

## Available Datasets

Each dataset is a property on the `Demo` class returning a [Polars](https://pola.rs) DataFrame, parsed on first access and cached. The headline datasets are decoded together in one parallel pass on first access, so pulling several is no more expensive than pulling one. See the [dataset reference](https://awpy.readthedocs.io/en/latest/datasets.html) for the full column list.

| Dataset | Description |
|---------|-------------|
| `rounds` | One row per round, reconstructed from `CCSGameRules` state — works even when `round_start` / `round_end` events are absent. Includes winner, side, and decoded round-end reason. |
| `kills` | Every `player_death` event, with attacker, victim, and assister each resolved to a Steam id, name, side, and world position. Flags each kill as a trade (`is_trade`) and each death as traded (`victim_traded`). |
| `damages` | Every `player_hurt` event, with attacker and victim resolved, plus the victim's health/armor before and after the hit. |
| `bomb` | Bomb actions (pickup, drop, plant start/finish, defuse) with the acting player, position, and bombsite. |
| `grenades` | Per-tick thrown-grenade trajectories (smoke, HE, flashbang, molotov, decoy). |
| `fires` | One row per burning inferno (molotov / incendiary), with position, thrower, and `[start_tick, end_tick]`. |
| `smokes` | One row per deployed smoke cloud, with position, thrower, and `[start_tick, end_tick]`. |
| `shots` | Every `weapon_fire` event with the shooter's state and active-weapon state (clip, inaccuracy, scoped). |
| `blinds` | One row per flash event: the thrower, the blinded player (both resolved), and the blind duration. |
| `item_events` | One row per weapon-item transaction — purchase, pickup, or drop — with the acting player, item, position, and (for buys) cost. |
| `stats` | One row per player: kills, deaths, assists, headshots, openings, trades, multikills, clutches (1v1–1v5), KAST, ADR, and utility (grenade damage, flashes thrown, enemies flashed, blind duration). |
| `round_economy` | One row per (round, side): team equipment value at freeze end and its buy-type classification (`eco` / `force` / `full`). |
| `players` | The roster: one row per player seen in the demo (Steam id, name, last side, and team/organization name). |
| `chat` | Chat messages decoded from `SayText` user messages, with channel (all/team). |
| `convars` | Server console variables (`mp_maxrounds`, ...) as a `dict[str, str]`. |
| `snapshots(*, ticks / every / seconds / events / start_tick / end_tick)` | Per-player game state (position, eye angles, health, armor, economy, and loadout) at a tick, a list of ticks, a contiguous range, or sampled across the match by a stride and/or event ticks. |

For events without a dedicated dataset, the `demo.events` mapping returns any game event as a DataFrame, and `ticks(props)` returns one row per player per tick for any networked properties.

The first dataset you touch decodes the headline datasets together, in parallel, and caches them — so `demo.kills` also readies `demo.damages`, `demo.rounds`, `demo.grenades`, and the rest. `ticks` and `snapshots` likewise decode in parallel across the demo's keyframes.

To discover what you can ask for without parsing first, `awpy.SNAPSHOT_PROPERTIES` maps each per-player snapshot feature to the engine property it comes from, and `awpy.GAME_EVENTS` catalogs the common game events (the ones actually in a demo are `demo.events.names`).

## Project Structure

| Crate | Description |
|-------|-------------|
| [`awpy`](crates/awpy) | Core parsing library (io, entity system, demo parser, name tables). |
| [`awpy-dev`](crates/awpy-dev) | Developer CLI for parser internals (the `awpy-dev` binary). |
| [`awpy-proto`](crates/awpy-proto) | Generated CS2 protobuf types (prost). |
| [`awpy-python`](crates/awpy-python) | Python bindings via PyO3 + Polars (published as `awpy` on PyPI). |

## Documentation

Full documentation is available at [awpy.readthedocs.io](https://awpy.readthedocs.io), including:

- [Getting Started](https://awpy.readthedocs.io/en/latest/getting-started.html)
- [Examples](https://awpy.readthedocs.io/en/latest/examples.html) — runnable scripts, also in [`crates/awpy-python/examples/`](crates/awpy-python/examples)
- [Datasets](https://awpy.readthedocs.io/en/latest/datasets.html)
- [API Reference](https://awpy.readthedocs.io/en/latest/api.html)
- [CLI Reference](https://awpy.readthedocs.io/en/latest/cli.html)
- [FAQ](https://awpy.readthedocs.io/en/latest/faq.html)
- [Changelog](https://awpy.readthedocs.io/en/latest/changelog.html)

## Development

```sh
# Rust
cargo fmt --all
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo nextest run --workspace --exclude awpy-python

# Python (from crates/awpy-python)
uv sync
uv run maturin develop
uv run pytest
uv run ruff check python tests
uv run ty check python
```

### Regenerating protobufs

`crates/awpy-proto/src/proto.rs` is generated from the `.proto` files in
`crates/awpy-proto/proto/` (synced from
[GameTracking-CS2](https://github.com/SteamDatabase/GameTracking-CS2)):

```sh
cargo run --manifest-path scripts/build-protos/Cargo.toml
```

## License

MIT — see [LICENSE](LICENSE) for details.
