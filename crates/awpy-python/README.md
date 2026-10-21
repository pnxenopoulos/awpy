# Awpy for Python

```python
from awpy import Demo

demo = Demo("match.dem")
demo.load("kills", "damages", "shots")
print(demo.header["map_name"])
print(demo.stats.select("name", "kills", "deaths", "assists", "adr", "kast"))
print(demo.snapshots(seconds=1.0))
```

Awpy parses Counter-Strike 2 (CS2) Source 2 demos with a Rust core.
The Python API uses PyO3 and returns typed Polars DataFrames.
Use Polars for filters, joins, and Apache Parquet output. Use matplotlib for plots.

## Install Awpy for Python

```bash
uv add awpy
# Or: pip install awpy
```

Use Python 3.11 or later and Polars 2.x.
Wheels support Python 3.11–3.15 on Linux, macOS, and Windows.
A wheel installation does not need a Rust compiler.

## Read CS2 events and player state with Awpy

Dataset properties cache their results. Use `demo.load(...)` to combine compatible
requests. `demo.events.names` lists recorded game events. Use `demo.events[name]`
for their raw fields, or `demo.kills` and `demo.damages` for resolved players.

```python
from awpy import Demo

demo = Demo("match.dem")
print(demo.events.names)
print(demo.events["player_death"])
print(demo.players)
print(demo.ticks(["health", "name"]))
```

Pass multipart recordings in order: `Demo(["match-p1.dem", "match-p2.dem"])`.
Multipart tables retain local ticks and add a zero-based `part` column.
Use `part=` for explicit tick queries. See the
[multipart guide](https://awpy.readthedocs.io/en/latest/datasets.html#multipart-demos).

## Check CS2 visibility and navigation with Awpy

```python
from awpy import NavMesh, VisibilityChecker

nav = NavMesh("de_inferno")
checker = VisibilityChecker("de_inferno")
start = (-158.6, 819.1, 103.7)
end = (1258.0, 455.5, 181.2)
print(nav.find_path(start, end))
print(checker.is_visible(start, end))
```

Map names use the newest cached awpy-data release. Missing assets download on
first access. Set `version=` to select a release, or pass a local `.nav` or
`.mesh` path. Coordinates use Hammer units, with Z vertical.

## Plot CS2 replay data with matplotlib

Install `uv add 'awpy[plot]'` or `pip install 'awpy[plot]'`.

```python
from awpy import Demo, plot

demo = Demo("match.dem")
deaths = demo.kills.select("victim_x", "victim_y", "victim_z").rows()
fig, ax = plot.heatmap(demo.header["map_name"], deaths, method="kde")
fig.savefig("deaths.png")
```

## Use the Awpy command line

```bash
awpy info match.dem
awpy stats match.dem --json
awpy get
```

See the [documentation](https://awpy.readthedocs.io/) for dataset columns,
map control, plots, and CLI commands. The [llms.txt index](https://awpy.readthedocs.io/llms.txt)
links to the main guides and API reference.
