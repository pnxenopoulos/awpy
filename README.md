<div align="center">

# Awpy

<p>
  <a href="https://discord.gg/W34XjsSs2H"><img src="https://img.shields.io/discord/868146581419999232?color=5865F2&label=Discord&logo=discord&logoColor=white&style=for-the-badge" alt="Awpy Discord"></a>
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

```python
from awpy import Demo

demo = Demo("match.dem")
demo.load("kills", "damages", "shots")
print(demo.header["map_name"])
print(demo.stats.select("name", "kills", "deaths", "assists", "adr", "kast"))
print(demo.snapshots(seconds=1.0))
```

Awpy parses [Counter-Strike 2](https://www.counter-strike.net/cs2) demo files in Rust. Its Python API returns typed [Polars](https://pola.rs) DataFrames.
Use Polars to filter and join results, write Apache Parquet files, or convert
tables to pandas. Use the plotting extra to draw CS2 data with matplotlib.

Awpy and the Deadlock parser [Boon](https://github.com/pnxenopoulos/boon) use the shared [pbdems2](https://github.com/pnxenopoulos/pbdems2) core. Awpy adds CS2 protobufs, field decoders, and name tables. See the [PBDEMS2 format guide](https://docs.rs/pbdems2/latest/pbdems2/guide/index.html) for the shared format.

## Table of Contents

- [Why Awpy?](#why-awpy)
- [Install Awpy](#installation)
- [Parse CS2 demos with Awpy](#quick-start)
- [Select Awpy datasets](#available-datasets)
- [Find Awpy workspace crates](#project-structure)
- [Read the Awpy documentation](#documentation)
- [Build and test Awpy](#development)
- [Awpy license](#license)

## Why Awpy?

- Read match events, player state, rounds, and statistics as DataFrames.
- Select the datasets, ticks, or entity properties that you need.
- Reconstruct rounds from game state, including demos without round events.
- Use the Python API, Rust library, or command-line interface.

<a id="installation"></a>

## Install Awpy

### Python

Use [uv](https://docs.astral.sh/uv/):

```bash
uv add awpy
```

You can also use pip:

```bash
pip install awpy
```

Python 3.11 or later is required. Awpy requires Polars 2.x.
Releases include wheels for Python 3.11–3.15 on Linux, macOS, and Windows.
Installing a wheel does not require a Rust compiler.

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

Add the Awpy Rust crate:

```toml
[dependencies]
awpy = "3.1"
```

<a id="quick-start"></a>

## Parse CS2 demos with Awpy

Use the Python example above to read a scoreboard and sample player state.
See the [getting started guide](https://awpy.readthedocs.io/en/latest/getting-started.html)
for installation, Polars queries, and map assets.

### Multipart demos

Pass files in recording order. Strings and `Path` objects can be mixed:

```python
from awpy import Demo

demo = Demo(["match-p1.dem", "match-p2.dem"])
print(demo.stats)
state = demo.snapshots(part=1, ticks=5333)
```

Multipart tables keep each file's ticks and add a zero-based `part` column.
`stats` and `players` combine Steam IDs. Explicit tick queries require `part`.
Awpy checks map, build, tick rate, round continuity, and recording boundaries.
Splits during live play are not supported. See the
[multipart guide](https://awpy.readthedocs.io/en/latest/datasets.html#multipart-demos).

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

<a id="available-datasets"></a>

## Select Awpy datasets

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

<a id="project-structure"></a>

## Find Awpy workspace crates

| Crate | Description |
|-------|-------------|
| [`awpy`](crates/awpy) | Core parsing library (io, entity system, demo parser, name tables). |
| [`awpy-dev`](crates/awpy-dev) | Developer CLI for parser internals (the `awpy-dev` binary). |
| [`awpy-proto`](crates/awpy-proto) | Generated CS2 protobuf types (prost). |
| [`awpy-python`](crates/awpy-python) | Python bindings via PyO3 + Polars (published as `awpy` on PyPI). |

<a id="documentation"></a>

## Read the Awpy documentation

See [awpy.readthedocs.io](https://awpy.readthedocs.io):

- [Getting Started](https://awpy.readthedocs.io/en/latest/getting-started.html)
- [Examples](https://awpy.readthedocs.io/en/latest/examples.html) — runnable scripts, also in [`crates/awpy-python/examples/`](crates/awpy-python/examples)
- [Datasets](https://awpy.readthedocs.io/en/latest/datasets.html)
- [API Reference](https://awpy.readthedocs.io/en/latest/api.html)
- [CLI Reference](https://awpy.readthedocs.io/en/latest/cli.html)
- [FAQ](https://awpy.readthedocs.io/en/latest/faq.html)
- [LLM documentation index](https://awpy.readthedocs.io/llms.txt)
- [Changelog](https://awpy.readthedocs.io/en/latest/changelog.html)

<a id="development"></a>

## Build and test Awpy

See [Contribute to Awpy](CONTRIBUTING.md) for branch names, development tools,
local checks, demo fixtures, and dependency updates.

### Releases

Update the package version and finalize the changelog. Push to `main` and wait
for **CI Check** to pass on the release commit.

In GitHub Actions, select **Release Awpy** (`release.yml`) on `main`.
Select `awpy-proto`, `awpy`, or `awpy-python` and enter its Cargo version.

Release in this order: `awpy-proto`, `awpy`, then the Python package.
The workflow checks that the preceding Rust package version is on crates.io.
Skip a Rust package if its version is already published.

Enter the full version without a leading `v`. The workflow checks the version,
publishes the package, then creates its tag and GitHub release. Tags use
`awpy-proto-v<version>`, `awpy-v<version>`, or `awpy-python-v<version>`.
Existing tags must refer to the release commit. A retry skips published files
and existing releases. A tag push does not start publication.

The `awpy-python` choice publishes a source archive and wheels for Python 3.11–3.15:

- Linux: x86-64 and ARM64.
- macOS: Intel and Apple silicon.
- Windows: x86-64.

Python 3.15 uses a stable-ABI wheel built with Python 3.14, as in CI.
Configure the crates.io trusted publishers for `release.yml` with environment
`crates`, and the PyPI trusted publisher for `release.yml` with environment `pypi`.
Update existing publishers that refer to the old workflow filenames.
Publish each new Rust crate once with an API token before you configure its
trusted publisher.

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

<a id="license"></a>

## Awpy license

MIT — see [LICENSE](LICENSE) for details.
