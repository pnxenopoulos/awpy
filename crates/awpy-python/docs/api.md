# 📚 API reference

## `Demo`

```python
from awpy import Demo

demo = Demo("match.dem")
```

A parsed Counter-Strike 2 demo file. Construction opens and memory-maps the file
and verifies its magic bytes.

**Parameters**

- **path** (`str | Path`) — path to the `.dem` file.

**Raises**

- `FileNotFoundError` — the file does not exist.
- `InvalidDemoError` — the file is not a valid CS2 demo.

### Properties

#### `header`

```python
demo.header  # -> dict
```

The demo file header and playback info: `map_name`, `server_name`,
`client_name`, `build_num`, `demo_version_name`, `game_directory`, and (when
available) `playback_ticks`, `playback_frames`, `playback_time`.

#### `path`

```python
demo.path  # -> pathlib.Path
```

The path the demo was opened from.

#### `events`

```python
demo.events                   # -> Events (see below)
demo.events.names             # -> list[str] — what the demo contains
demo.events.player_death      # -> polars.DataFrame
demo.events["player_ping"]    # -> polars.DataFrame
```

The demo's game events, keyed by name. The event stream is parsed on first
access and cached; each event's DataFrame is built on demand and cached too.

#### Datasets

```python
demo.rounds     # -> polars.DataFrame
demo.kills      # -> polars.DataFrame
demo.damages    # -> polars.DataFrame
demo.bomb       # -> polars.DataFrame
demo.grenades   # -> polars.DataFrame
demo.fires      # -> polars.DataFrame
demo.smokes     # -> polars.DataFrame
demo.shots      # -> polars.DataFrame
demo.blinds     # -> polars.DataFrame
demo.item_events  # -> polars.DataFrame
demo.stats      # -> polars.DataFrame
```

The headline datasets, each parsed on first access and cached. See
{doc}`datasets` for every column.

#### `players`

```python
demo.players  # -> polars.DataFrame: steamid, name, side
```

The roster — every player seen in the demo, with the last side they were
observed on (players swap at halftime). Bots have `steamid` 0.

#### `chat`

```python
demo.chat  # -> polars.DataFrame: tick, entity_index, name, message, channel
```

Chat messages, decoded from `SayText` / `SayText2` user messages. `channel`
distinguishes all-chat (`Cstrike_Chat_All`) from team chat (`Cstrike_Chat_T`
/ `Cstrike_Chat_CT`). Server-side demos may strip chat entirely.

#### `convars`

```python
demo.convars                  # -> dict[str, str]
demo.convars["mp_maxrounds"]  # -> "24"
```

The server's console variables from the demo's `net_SetConVar` messages —
`mp_maxrounds`, `mp_freezetime`, `mp_overtime_enable`, and friends. When a
convar is set more than once, the last value wins.

### Methods

#### `snapshots(*, ticks=None, every=None, seconds=None, events=None, start_tick=None, end_tick=None)`

```python
demo.snapshots(ticks=29000)                       # one moment (fast seek)
demo.snapshots(ticks=[29000, 30000])              # specific ticks
demo.snapshots(start_tick=29000, end_tick=30000)  # a contiguous range
demo.snapshots(every=64)                          # every 64 ticks
demo.snapshots(seconds=1.0)                        # ~1 sample / second
demo.snapshots(events="player_death")             # at kill ticks
demo.snapshots(every=64, start_tick=0, end_tick=64000)  # bounded stride
```

The go-to reader for **curated player state** — position, eye angles, health,
armor, economy, and loadout in one fixed, resolved schema (the full column list
is in the {doc}`Reference <reference>`; also `awpy.SNAPSHOT_PROPERTIES`). Choose
the ticks with any combination of `ticks` (an int or a list), a stride (`every`
/ `seconds`), `events`, and a `start_tick` / `end_tick` window — given on their
own, the window is a contiguous range. A single `ticks` value seeks directly
(fast); everything else decodes in parallel. Rows map directly onto
{doc}`plot <plot>`'s `Player` markers. When the fixed schema isn't enough — a
raw property, non-player entities, or a leaner column set over every tick — use
`ticks` (below).

#### `ticks(props=None, players_only=True)`

```python
demo.ticks()                              # -> polars.DataFrame
demo.ticks(["health", "m_iTeamNum"])
```

The **raw, low-level reader** beneath `snapshots` (above) — use it when the
curated snapshot schema can't give you what you need: a raw or derived network
property (any CS2 field, e.g. `m_vecVelocity[0]`), non-player entities
(`players_only=False`), or a lean subset of columns over every tick.

With `players_only=True` (default): **one row per player per tick**, keyed by
`steamid`, with each requested property natively typed (Int64 / Float64 /
Boolean / Utf8). `props` defaults to `["X", "Y", "Z", "health", "armor",
"team_num"]` and accepts friendly aliases (`X`/`Y`/`Z` for computed world
position, `health`, `armor`, `team_num`, `name`, `money`) or raw CS2 field
names. Decoded in parallel across keyframe segments. With `players_only=False`,
one row per (tick, entity) with columns `tick`, `entity_id`, `class_name`, then
the properties.

#### `player_stats(include_knife_rounds=False)`

```python
demo.stats                                    # -> polars.DataFrame (cached, no knife rounds)
demo.player_stats(include_knife_rounds=True)  # -> polars.DataFrame (counts knife rounds)
```

The same per-player scoreboard as the `stats` property, but with control over
knife rounds (excluded by default — see {doc}`datasets`). Unlike the cached
`stats` property, this method **recomputes on every call** (it re-runs the
kill/damage entity pass) and is not cached, so it costs a few seconds per call
on a large demo. Prefer `demo.stats` for the default result; use this method
only for `include_knife_rounds=True`, and hold onto the DataFrame it returns.

## `Events`

```python
events = demo.events
```

A read-only mapping from event name to DataFrame, returned by `demo.events`.
Each frame has a `tick` column plus one string column per event key (e.g.
`attacker`, `weapon`, `headshot` for `player_death`).

| Member | Type | Description |
| --- | --- | --- |
| `names` | `list[str]` | Event names present in the demo, sorted. |
| `counts` | `dict[str, int]` | Occurrences per event name. |
| `events.<name>` / `events[name]` | `polars.DataFrame` | One event's rows (built once, cached). Unknown names raise `AttributeError` / `KeyError`. |
| `name in events`, `iter(events)`, `len(events)` | | Standard mapping behavior over the names. |

## `VisibilityChecker`

```python
from awpy import VisibilityChecker

vc = VisibilityChecker("de_inferno")            # map name -> cached release
vc = VisibilityChecker("de_inferno", version="14018")  # a pinned release
vc = VisibilityChecker("path/to/de_inferno.mesh")      # an explicit file
```

Line-of-sight over a map's collision mesh. Building the checker loads the `.mesh`
and builds a bounding-volume hierarchy once; reuse it across queries. See
{doc}`visibility`.

**Parameters**

- **source** (`str | Path`) — a **map name** (a bare string like `"de_inferno"`,
  resolved through {func}`awpy.data.mesh_path` using the newest cached release),
  or a path to a `.mesh` file.
- **version** (`str`, keyword-only) — pin a specific map-data release; valid only
  when `source` is a map name.

**Raises**

- `FileNotFoundError` — the file does not exist.
- `ValueError` — the file is not a valid awpy mesh, or `version=` was combined
  with a file path.

### Methods & properties

#### `is_visible(a, b)` / `is_occluded(a, b)`

```python
vc.is_visible((x0, y0, z0), (x1, y1, z1))  # -> bool
```

Whether the straight segment between two `(x, y, z)` world points (Hammer units,
Z-up) is clear (`is_visible`) or blocked (`is_occluded`).

#### `triangle_count`

```python
vc.triangle_count  # -> int
```

Triangles in the loaded mesh.

#### `path`

```python
vc.path  # -> pathlib.Path | None
```

The file the mesh was loaded from.

## `NavMesh`

```python
from awpy import NavMesh

nav = NavMesh("de_dust2")
```

A map's navigation mesh — walkable **areas** and the **connections** between
them. Locates the area a world point sits in and finds shortest area-to-area
paths. See {doc}`nav`.

**Parameters**

- **source** (`str | Path`) — a map name (e.g. `"de_dust2"`) or path to a `.nav`
  file (e.g. from {func}`awpy.data.nav_path`).
- **version** (`int | None`) — `awpy-data` release when `source` is a map name;
  defaults to the newest cached release.

**Raises**

- `FileNotFoundError` — the file does not exist, or the release has no nav for
  the map.
- `ValueError` — the file is not a valid nav mesh, or `version` is combined with
  a file path.

Areas are identified by a numeric `area_id`.

### Methods & properties

| Member | Type | Description |
| --- | --- | --- |
| `areas` | `polars.DataFrame` | One row per area: `area_id`, `hull_index`, `dynamic_attribute_flags`, `n_corners`, `centroid_x/y/z`, `size`, `n_connections`. |
| `area(area_id)` | `dict \| None` | Full detail for one area, including `corners`, `connections`, `ladders_above/below`, `centroid`, `size`. |
| `find_area(point)` | `int \| None` | Area containing an `(x, y, z)` world point (nearest by height when floors overlap). |
| `neighbors(area_id)` | `list[int]` | Distinct areas reachable directly. |
| `find_path(start, end, *, weight="distance")` | `list[int]` | Shortest area path (inclusive); endpoints are area ids or points. `weight` is `"distance"` (3D centroid distance), `"hops"` (fewest areas), or `"size"` (routes away from large areas). |
| `version`, `sub_version` | `int` | Nav-mesh format version (CS2 ships 36). |
| `is_analyzed` | `bool` | Whether bot-navigation data was generated. |
| `area_count`, `len(nav)` | `int` | Number of areas. |
| `path` | `Path \| None` | The file the nav was loaded from. |

## `awpy.data`

```python
from awpy import data
```

Downloads and caches CS2 map assets from the
[`awpy-data`](https://github.com/pnxenopoulos/awpy-data) releases under
`$HOME/.awpy/<version>/` (override with `AWPY_DATA_DIR`). See {doc}`visibility`.
Every function takes an optional `version=` (a `ClientVersion` tag); omit it for
the latest release.

| Function | Returns | Description |
| --- | --- | --- |
| `mesh_path(map, version=None)` | `Path` | Collision `.mesh` for `VisibilityChecker`. |
| `nav_path(map, version=None)` | `Path` | Nav mesh `.nav`. |
| `radar_path(map, version=None, *, lower=False)` | `Path` | Radar `.png` (`lower=True` for a multi-level map's lower radar). |
| `map_data(version=None)` | `dict` | Per-map world→radar transform (`map_data.json`). |
| `manifest(version=None)` | `dict` | Version identifiers + per-file checksums. |
| `available_maps(version=None)` | `list[str]` | Map names in the release. |
| `latest_version()` | `str` | Latest release tag (queries the GitHub API). |
| `resolve_version(version=None)` | `str` | Concrete tag for `version` (latest if `None`). |
| `local_versions()` | `list[str]` | Release versions already cached locally, oldest first. |
| `data_dir(version=None)` | `Path` | Local cache directory for a release. |
| `update(version=None, *, force=False)` | `Path` | Download every asset for a release. |
| `clear(version=None)` | `None` | Delete one release's cache, or the whole cache. |

## Exceptions

### `InvalidDemoError`

```python
from awpy import InvalidDemoError
```

Raised when a file is not a valid CS2 demo (bad magic bytes or a parse error).
