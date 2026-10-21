# Get started with Awpy

```python
from awpy import Demo

demo = Demo("match.dem")
demo.load("kills", "damages", "shots")
print(demo.header["map_name"])
print(demo.stats.select("name", "kills", "deaths", "assists", "adr", "kast"))
print(demo.snapshots(seconds=1.0))
```

Awpy reads Counter-Strike 2 (CS2) Source 2 `.dem` recordings.
Its Rust parser returns Polars DataFrames through the Python API.
Replace `match.dem` with a local replay. The older CS:GO format is not supported.

<a id="install"></a>

## Install Awpy and its plotting extra

```bash
uv add awpy
uv add 'awpy[plot]'  # Optional matplotlib plots.
# Or: pip install 'awpy[plot]'
```

Use Python 3.11 or later and Polars 2.x. Wheels support Python 3.11–3.15 on
Linux, macOS, and Windows. A wheel installation does not need Rust.

<a id="get-a-demo"></a>

## Get a CS2 demo for Awpy

Download recordings from the CS2 match history, a tournament match page, or
your match platform. CS2 stores downloaded recordings in
`Counter-Strike Global Offensive/game/csgo/replays/`.

<a id="open-a-demo"></a>

## Open CS2 files with Awpy Demo

```python
from pathlib import Path
from awpy import Demo

demo = Demo(Path("match.dem"))
print(demo.header)
print(demo.tick_rate)
```

Single-file construction maps the file and checks its header. A missing file
raises `FileNotFoundError`. Invalid data raises `InvalidDemoError`.
Later decoding can also fail for an incomplete or corrupt recording.

<a id="the-datasets"></a>

## Read Awpy datasets with Polars

```python
import polars as pl
from awpy import Demo

demo = Demo("match.dem")
demo.load("kills", "damages", "shots")
headshots = demo.kills.filter(pl.col("headshot"))
print(headshots.group_by("attacker_name").len().sort("len", descending=True))
print(demo.rounds.select("round_num", "winner_side", "reason_name"))
print(demo.stats.sort("adr", descending=True))
```

Dataset properties cache their DataFrames. `load()` combines compatible requests
and skips cached inputs. Use {doc}`datasets` for columns and {doc}`reference`
for ADR, KAST, trades, and other metric definitions.

<a id="players-chat-and-server-settings"></a>

## Read Awpy players, chat, and server settings

```python
from awpy import Demo

demo = Demo("match.dem")
print(demo.players)
print(demo.chat)
print(demo.convars.get("mp_maxrounds"))
```

Join players by `steamid`. Keep Steam IDs as Polars `UInt64` values.
The roster's `side` is the last observed side; sides change at halftime.
`team_clan_name` records the team name when the server supplies it.
Chat can be empty when the replay contains no supported messages.

<a id="any-game-event"></a>

## Read raw CS2 game events with Awpy

```python
from awpy import Demo

demo = Demo("match.dem")
print(demo.events.names)
print(demo.events.counts)
print(demo.events["player_death"])
```

Raw event frames have a `tick` column and string columns for event fields.
Fields such as `attacker` contain user IDs. Use the dedicated `kills` and
`damages` tables for resolved Steam IDs and positions.

<a id="game-state-at-any-moment"></a>

## Select Awpy player snapshots and entity properties

```python
from awpy import Demo

demo = Demo("match.dem")
state = demo.snapshots(seconds=1.0)
kill_ticks = demo.snapshots(events="player_death")
properties = demo.ticks(["health", "m_iTeamNum"])
print(state.select("tick", "steamid", "health", "inventory"))
```

Use `ticks=10000` for one demo tick, or `ticks=[10000, 10100]` for several.
Use `start_tick` and `end_tick` for an inclusive window.
`ticks()` reads selected properties at every recorded tick.
These two methods run for each call; retain their results for reuse.

<a id="maps-line-of-sight-and-radar-assets"></a>

## Check CS2 lines of sight with Awpy

```python
from awpy import NavMesh, VisibilityChecker

start = (-158.6, 819.1, 103.7)
end = (1258.0, 455.5, 181.2)
checker = VisibilityChecker("de_inferno")
nav = NavMesh("de_inferno")
print(checker.is_visible(start, end))
print(nav.find_path(start, end))
```

Positions use Hammer units, with Z vertical. Map names resolve through
[awpy-data](https://github.com/pnxenopoulos/awpy-data).
Missing assets download to `~/.awpy`. Set `version=` to select a game release.
The visibility check uses static collision geometry. See {doc}`visibility` and {doc}`nav`.

<a id="draw-it"></a>

## Plot CS2 death positions with Awpy and matplotlib

```python
from awpy import Demo, plot

demo = Demo("match.dem")
deaths = demo.kills.select("victim_x", "victim_y", "victim_z").rows()
fig, ax = plot.heatmap(demo.header["map_name"], deaths, method="kde")
fig.savefig("deaths.png")
```

Install the `awpy[plot]` extra first. See {doc}`plot` for player markers,
map levels, navigation areas, and animated GIFs.
Use {doc}`map_control` for area-control estimates.

<a id="the-command-line"></a>

## Inspect CS2 demos with the Awpy CLI

```bash
awpy info match.dem
awpy stats match.dem
awpy events match.dem --summary
awpy rounds match.dem --json
awpy get
```

The Python package installs `awpy` and `python -m awpy`. See {doc}`cli`.

<a id="multipart-recordings"></a>

## Read multipart CS2 recordings with Awpy

```python
from awpy import Demo

demo = Demo(["match-p1.dem", "match-p2.dem"])
print(demo.stats)
state = demo.snapshots(part=1, ticks=10000)
```

Pass paths in recording order. Strings and `Path` objects can be mixed.
Multipart tables add `part` and retain local ticks. Explicit tick queries need
`part=`. Awpy checks recording compatibility and completed round boundaries.
Splits during live play are not supported. See {doc}`datasets`.

<a id="where-next"></a>

## Find Awpy examples and API details

Use {doc}`examples` for complete scripts, {doc}`datasets` for columns,
and {doc}`api` for function parameters and return types.
