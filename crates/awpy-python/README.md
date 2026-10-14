# awpy

Python bindings for [Awpy](https://github.com/pnxenopoulos/awpy), a
Counter-Strike 2 demo parser with a Rust backend.

Awpy requires Python 3.11 or later and Polars 2.x.
Wheels support Python 3.11–3.15 on Linux, macOS, and Windows.
Installing a wheel does not require a Rust compiler.

```python
from awpy import Demo

demo = Demo("match.dem")

# File header + playback info
print(demo.header["map_name"])

# Cached Polars DataFrames
demo.load("rounds", "kills", "damages")
rounds = demo.rounds
kills = demo.kills
damages = demo.damages

# Any game event, long-form (demo.events.names lists them)
pings = demo.events.player_ping

# Roster, chat, server config, and game state at a moment (or sampled)
demo.players
demo.chat
demo.convars["mp_maxrounds"]
demo.snapshots(ticks=29000)          # every player's state at one tick
demo.snapshots(every=64)      # ... sampled across the match

# Per-tick player state — one row per player per tick, decoded in parallel
demo.ticks()                  # default: X, Y, Z, health, armor, team_num
demo.ticks(["health", "m_iTeamNum"])
```

Line-of-sight, using map geometry fetched on demand:

```python
from awpy import VisibilityChecker

vc = VisibilityChecker("de_inferno")  # newest cached awpy-data release; downloads if needed
vc.is_visible((1258.04, 455.47, 181.22), (-158.62, 819.09, 103.73))  # -> True

VisibilityChecker("de_inferno", version=2000873)   # pin an awpy-data release
VisibilityChecker("path/to/de_inferno.mesh")       # or load a mesh file directly
```

Find nav areas and routes:

```python
from awpy import NavMesh

nav = NavMesh("de_inferno")               # newest cached awpy-data release
a = nav.find_area((-158.6, 819.1, 103.7)) # area id at a world point
b = nav.find_area((1258.0, 455.5, 181.2))
path = nav.find_path(a, b)                 # area ids along the shortest path
```

Install `awpy[plot]` to draw frames and heatmaps:

```python
from awpy import plot

deaths = demo.kills.select(["victim_x", "victim_y", "victim_z"]).rows()
fig, ax = plot.heatmap("de_inferno", deaths, method="kde")

fig, ax = plot.frame("de_inferno", [plot.Player(x=-158.6, y=819.1, side="ct", hp=87)])
```

Installing the package also installs the `awpy` command — demo inspection
(`awpy info`, `awpy kills`, `awpy stats`, ... with `--json` output) and
map-data management (`awpy get`, `awpy versions`, `awpy maps`, `awpy clear`).

See the [documentation](https://awpy.readthedocs.io) for the API,
dataset reference, and CLI guide.

Built with [PyO3](https://pyo3.rs) and [Polars](https://pola.rs).
