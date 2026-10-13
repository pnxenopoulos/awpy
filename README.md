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

Awpy parses [Counter-Strike 2](https://www.counter-strike.net/cs2) demo files in Rust. Its Python API returns [Polars](https://pola.rs) DataFrames.

Awpy and the Deadlock parser [Boon](https://github.com/pnxenopoulos/boon) use the shared [pbdems2](https://github.com/pnxenopoulos/pbdems2) core. Awpy adds CS2 protobufs, field decoders, and name tables. See the [PBDEMS2 format guide](https://docs.rs/pbdems2/latest/pbdems2/guide/index.html) for the shared format.

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

- Read match events, player state, rounds, and statistics as DataFrames.
- Select the datasets, ticks, or entity properties that you need.
- Reconstruct rounds from game state, including demos without round events.
- Use the Python API, Rust library, or command-line interface.

## Installation

### Python

Use [uv](https://docs.astral.sh/uv/):

```bash
uv add awpy
```

You can also use pip:

```bash
pip install awpy
```

Python 3.11 or later is required. Pre-built wheels do not need a Rust compiler.

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

Dataset properties return cached DataFrames. Use `demo.load("kills", "damages", "shots")` to collect compatible datasets in one pass. See the [dataset reference](https://awpy.readthedocs.io/en/latest/datasets.html) for columns and selection rules.

| Dataset | Description |
|---------|-------------|
| `rounds` | Round timings, winners, and end reasons from game state. |
| `kills` | Kills, participants, positions, and trade flags. |
| `damages` | Damage events, participants, and health and armor changes. |
| `bomb` | Bomb actions (pickup, drop, plant start/finish, defuse) with the acting player, position, and bombsite. |
| `grenades` | Per-tick thrown-grenade trajectories (smoke, HE, flashbang, molotov, decoy). |
| `fires` | One row per burning inferno (molotov / incendiary), with position, thrower, and `[start_tick, end_tick]`. |
| `smokes` | One row per deployed smoke cloud, with position, thrower, and `[start_tick, end_tick]`. |
| `shots` | Every `weapon_fire` event with the shooter's state and active-weapon state (clip, inaccuracy, scoped). |
| `blinds` | One row per flash event: the thrower, the blinded player (both resolved), and the blind duration. |
| `item_events` | One row per weapon-item transaction — purchase, pickup, or drop — with the acting player, item, position, and (for buys) cost. |
| `stats` | Player statistics, including KAST, ADR, trades, clutches, and utility. |
| `round_economy` | One row per (round, side): team equipment value at freeze end and its buy-type classification (`eco` / `force` / `full`). |
| `players` | The roster: one row per player seen in the demo (Steam id, name, last side, and team/organization name). |
| `chat` | Recorded chat messages and channels. |
| `convars` | Server console variables (`mp_maxrounds`, ...) as a `dict[str, str]`. |
| `snapshots(*, ticks / every / seconds / events / start_tick / end_tick)` | Per-player game state (position, eye angles, health, armor, economy, and loadout) at a tick, a list of ticks, a contiguous range, or sampled across the match by a stride and/or event ticks. |

For events without a dedicated dataset, the `demo.events` mapping returns any game event as a DataFrame, and `ticks(props)` returns one row per player per tick for any networked properties.

Use `awpy.SNAPSHOT_PROPERTIES` to find snapshot fields and their engine properties. `awpy.GAME_EVENTS` lists common events; `demo.events.names` lists events in the demo.

## Project Structure

| Crate | Description |
|-------|-------------|
| [`awpy`](crates/awpy) | Core parsing library (io, entity system, demo parser, name tables). |
| [`awpy-dev`](crates/awpy-dev) | Developer CLI for parser internals (the `awpy-dev` binary). |
| [`awpy-proto`](crates/awpy-proto) | Generated CS2 protobuf types (prost). |
| [`awpy-python`](crates/awpy-python) | Python bindings via PyO3 + Polars (published as `awpy` on PyPI). |

## Documentation

See [awpy.readthedocs.io](https://awpy.readthedocs.io):

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
uv sync --locked --no-install-project
uv run --no-sync maturin develop --release
uv run --no-sync pytest -m "not fixtures"
uv run --no-sync ruff check python tests
uv run --no-sync ty check python
```

### Python tests

The `fixtures` marker selects all tests that need demo files, including schema,
CLI, and example tests. CI runs these tests in a separate job. Run the offline
tests with `pytest -m "not fixtures"`. Unknown markers and configuration keys
are errors.

For demo-backed tests, fetch the fixture manifest and allow downloads. Run these
commands from `crates/awpy-python` after the development install:

```sh
mkdir -p tests/fixtures
curl -fSL https://raw.githubusercontent.com/pnxenopoulos/awpy-fixtures/main/manifest.json \
  -o tests/fixtures/manifest.json
AWPY_RUN_FIXTURES=1 uv run --no-sync pytest -m fixtures --durations=10
```

By default, `pytest` uses cached demos and skips unavailable demos.
`AWPY_RUN_FIXTURES=1` permits downloads and makes missing required demos or an
empty manifest fail the tests.

For a faster run, prepare the files before starting two test workers:

```sh
uv run --no-sync python tests/fixture_store.py
AWPY_RUN_FIXTURES=1 AWPY_TICK_SEGMENTS=2 POLARS_MAX_THREADS=2 \
  uv run --no-sync pytest -m fixtures -n 2 --dist=loadfile --durations=10
```

CI uses two workers and assigns complete test files to each worker. This keeps
module fixtures shared. Use one worker if memory is limited. Avoid `-n auto`:
each worker can also start parser and Polars threads.

Fixtures verify each demo file once per worker session. Read-only checks share
a parsed demo within a module or parameter; cache and parser-state tests create
fresh instances. Do not change the cached DataFrames on a shared demo. Temporary asset
caches and monkeypatches remain local to each test.

CI installs dependencies from the lockfile and tests the prebuilt wheel with
`uv run --no-sync`. This prevents uv from replacing the wheel with a source
build. Keep timing reports enabled when changing fixtures or test scheduling.

Each test checks one behavior. Several assertions can describe the same result.
Use named tests for independent results and parameters for input variants.
Share expensive, unchanged query results through module fixtures.
Keep mutable test doubles, files, and settings local to each test.
Remove duplicate checks only when the same behavior and parsing path remain covered.
Use exact DataFrame comparisons when the result must match exactly.

### Parsing benchmarks

Run the Criterion suite with a local demo:

```sh
AWPY_BENCH_DEMO=/absolute/path/to/match.dem cargo criterion -p awpy --bench parse
```

See the [benchmark guide](crates/awpy/benches/README.md) for runner installation,
workload filters, fixed parallelism, and baseline comparisons.

Use the [Python API benchmark guide](crates/awpy-python/benchmarks/README.md)
for isolated timing, peak memory, and output checks through `Demo`.

### Regenerating protobufs

`crates/awpy-proto/src/proto.rs` is generated from the `.proto` files in
`crates/awpy-proto/proto/` (synced from
[GameTracking-CS2](https://github.com/SteamDatabase/GameTracking-CS2)):

```sh
cargo run --locked --manifest-path scripts/build-protos/Cargo.toml
```

The generator uses a bundled `protoc`. It removes unsupported C++ annotations
from temporary compiler inputs. It keeps the upstream `.proto` files unchanged.
Run its tests with `cargo test --locked --manifest-path scripts/build-protos/Cargo.toml`.

## License

MIT — see [LICENSE](LICENSE) for details.
