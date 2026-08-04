# Awpy

Awpy is a fast [Counter-Strike 2](https://www.counter-strike.net/cs2) demo parser written in Rust with native Python bindings. It reads Source 2 demo files (`.dem`) and returns [Polars](https://pola.rs) DataFrames, giving you structured access to match data without touching the binary format yourself.

## Why Awpy?

CS2 demo files hold a wealth of match data — player positions, kills, damage, round outcomes, and more — but the Source 2 demo format is complex and undocumented. Awpy handles the low-level parsing so you can focus on analysis.

- ⚡ **Fast.** The core parser is written in Rust. A full match parses in seconds.
- 📊 **Structured output.** Datasets come back as Polars DataFrames, ready for filtering, grouping, joins, and plotting.
- 🎯 **Parse only what you need.** Ask for one event or a handful of entity properties and Awpy skips the rest.
- 🔫 **CS2-aware.** Rounds are reconstructed from game-rules state; kills and damage carry every field; hit groups and round-end reasons are decoded to names.
- 👁️ **Line-of-sight.** `VisibilityChecker` answers whether two world points can see each other, using collision meshes fetched by `awpy.data`.
- 🧭 **Navigation meshes.** `NavMesh` locates a point's map area and finds shortest paths across a map's nav graph.
- 🗺️ **Map control.** `awpy.map_control` scores how much of the map each team holds at any tick — by raycast (line of sight in any direction), vision (clipped to each player's 90° field of view), or reachability (who arrives first, molotov-aware).
- 📈 **Plotting.** `awpy.plot` draws game states, heatmaps, nav meshes, and map control on radar images (`pip install 'awpy[plot]'`).
- 💻 **CLI included.** `pip install awpy` also gives you the `awpy` command — demo inspection and map-data downloads without writing any code.

## Get started

Install with `uv add awpy` or `pip install awpy`, then head to {doc}`getting-started` for a walkthrough, or {doc}`examples` for complete scripts you can run. If something's off, open a [GitHub issue](https://github.com/pnxenopoulos/awpy/issues).

```python
from awpy import Demo

demo = Demo("match.dem")
print(demo.header["map_name"])

rounds = demo.rounds    # round_num, winner_side, reason_name, ...
kills = demo.kills      # every player_death, all fields
```

## Useful links

- [Counter-Strike 2](https://www.counter-strike.net/cs2) — official home page
- [Awpy on GitHub](https://github.com/pnxenopoulos/awpy)
- [Polars](https://pola.rs) — the DataFrame library Awpy returns data in
- [pbdems2](https://docs.rs/pbdems2/latest/pbdems2/guide/index.html) — the shared Source 2 demo-format core and its format guide
- [Boon](https://github.com/pnxenopoulos/boon) — sister project: a [Deadlock](https://store.steampowered.com/app/1422450/Deadlock/) demo parser with the same Rust-core, Polars-out design
- [deadlock.nyc](https://deadlock.nyc/) — sister project: a fully client-side Deadlock demo viewer that runs in your browser

```{toctree}
:maxdepth: 2
:hidden:
:caption: Start here

getting-started
examples
faq
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Match data

datasets
reference
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Maps & space

visibility
nav
map_control
plot
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Interfaces

api
cli
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: About

other-parsers
changelog
```
