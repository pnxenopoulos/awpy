# 🧭 Navigation meshes

Every CS2 map ships a **navigation mesh** — the surface the game's bots walk on,
tiled into convex polygonal **areas** that are wired together by **connections**
(which area you can step into, and from which edge). It's a compact model of
"where you can stand and how areas join up," useful for tagging positions,
measuring routes, and reasoning about map control.

Awpy parses these `.nav` files — published by
[`awpy-data`](https://github.com/pnxenopoulos/awpy-data) alongside the collision
meshes and radars — and answers the two questions you'd actually ask of one:
**which area is this point in**, and **what's the shortest path between two
areas**.

```{figure} img/nav-mesh.webp
:alt: Dust 2's navigation mesh drawn over its radar image, with 2242 walkable areas outlined in amber
:width: 100%

Dust 2's 2,242 nav areas, drawn with {func}`awpy.plot.nav`. The tiling is
finer in the chokepoints and coarser across open ground — area size tracks how
much detail the bots need, which is why `weight="size"` routes away from open
areas.
```

## `NavMesh`

```python
from awpy import NavMesh

nav = NavMesh("de_dust2")

nav.find_area((-1500.0, 900.0, 60.0))   # -> an area id, e.g. 812
nav.find_path(812, 42)                   # -> [812, ..., 42]  (area ids along the way)
```

The constructor takes a map name or a `.nav` file:

```python
NavMesh("de_dust2")                  # newest release cached under ~/.awpy
                                     # (downloads the latest if none is cached)
NavMesh("de_dust2", version=2000873) # pin an awpy-data release
NavMesh("path/to/de_dust2.nav")      # load a specific .nav file
```

A string counts as a file path when it ends in `.nav` or contains a path
separator; a `pathlib.Path` always does. Anything else is treated as a map name
and resolved through `awpy.data.nav_path`.

Points are `(x, y, z)` tuples (or lists) in **Hammer units, Z-up** — the same
frame as demo world positions, so the `*_x` / `*_y` / `*_z` columns from
`demo.kills`, `demo.grenades`, `demo.snapshots(...)`, etc. pass straight in.

Areas are identified by a numeric `area_id`; `find_area` returns that id.

### Areas

`nav.areas` is a DataFrame with one row per area — the analysis-friendly view:

```python
nav.areas
# shape: (2_248, 9)
# ┌─────────┬────────────┬─────────────────────────┬───────────┬───┬──────┬───────────────┐
# │ area_id ┆ hull_index ┆ dynamic_attribute_flags ┆ n_corners ┆ … ┆ size ┆ n_connections │
# ╞═════════╪════════════╪═════════════════════════╪═══════════╪═══╪══════╪═══════════════╡
# │ 1       ┆ 0          ┆ 0                       ┆ 4         ┆ … ┆ 520… ┆ 1             │
# │ …       ┆ …          ┆ …                       ┆ …         ┆ … ┆ …    ┆ …             │
```

| Column | Description |
| --- | --- |
| `area_id` | Unique id of the area. |
| `hull_index` | Collision hull the area was generated for. |
| `dynamic_attribute_flags` | Engine attribute bitset (bomb-target, defuse, …). |
| `n_corners` | Number of polygon corners. |
| `centroid_x` / `_y` / `_z` | Geometric center of the polygon. |
| `size` | 2D area of the polygon (Hammer units²). |
| `n_connections` | Distinct neighbouring areas. |

For the full geometry of a single area — its corners and neighbour ids — use
`nav.area(area_id)`:

```python
nav.area(1)
# {'area_id': 1, 'hull_index': 0, 'dynamic_attribute_flags': 0,
#  'corners': [(150.5, 10.5, 12.0), (185.0, 21.0, 10.0), ...],
#  'connections': [3], 'ladders_above': [], 'ladders_below': [],
#  'centroid': (162.5, 25.1, 11.0), 'size': 520.9}
```

### Queries

```python
area = nav.find_area((x, y, z))    # area containing a world point (or None)
nav.neighbors(area)                # -> [ids reachable directly]
nav.find_path(start, end)          # -> [ids] from start to end, inclusive
```

`find_area` handles overlapping floors: when several areas cover the same
`(x, y)` (a bridge over a tunnel, stacked levels), it returns the one whose
height is closest to the point's `z`.

`find_path` accepts **either** an area id **or** a point for each endpoint (a
point is resolved with `find_area` first), and returns the list of area ids from
`start` to `end` inclusive — or an empty list if either endpoint maps to no area
or no route connects them. Connections are directional, matching the mesh.

Edges can be weighted three ways:

```python
nav.find_path(a, b, weight="distance")  # default: 3D distance between centroids
nav.find_path(a, b, weight="hops")      # fewest areas
nav.find_path(a, b, weight="size")      # sum of area sizes; routes away from large areas
```

Pass a route straight to {func}`awpy.plot.nav` to see it:

```python
from awpy.plot import nav as plot_nav

route = nav.find_path((-680.0, 1500.0, 0.0), (1200.0, 2400.0, 0.0))
fig, ax = plot_nav("de_dust2", highlight=route)
```

```{figure} img/nav-path.webp
:alt: The same Dust 2 nav mesh with a 70-area route highlighted in cyan, running from T spawn through mid toward the A site
:width: 100%

A 70-area route highlighted with `highlight=`. Because `find_path` returns plain
area ids, anything you can express as a set of areas — a route, a bombsite, the
output of your own search — can be drawn the same way.
```

| Member | Type | Description |
| --- | --- | --- |
| `NavMesh(source, *, version=None)` | | Load a map's nav (or a `.nav` file). Raises `FileNotFoundError` / `ValueError`. |
| `areas` | `polars.DataFrame` | One row per area (see above). |
| `area(area_id)` | `dict \| None` | Full detail for one area, including `corners` and `connections`. |
| `find_area(point)` | `int \| None` | Area containing an `(x, y, z)` point. |
| `neighbors(area_id)` | `list[int]` | Distinct areas reachable directly. |
| `find_path(start, end, *, weight="distance")` | `list[int]` | Shortest area path; endpoints are ids or points. |
| `version` / `sub_version` | `int` | Nav-mesh format version (CS2 ships 36). |
| `is_analyzed` | `bool` | Whether bot-navigation data was generated. |
| `area_count` / `len(nav)` | `int` | Number of areas. |
| `path` | `Path \| None` | The file the nav was loaded from. |

### Example: tag every kill with its area

```python
import polars as pl
from awpy import Demo, NavMesh

demo = Demo("match.dem")
nav = NavMesh(demo.header["map_name"])

kills = demo.kills.with_columns(
    pl.Series(
        "victim_area",
        [
            nav.find_area((r["victim_x"], r["victim_y"], r["victim_z"]))
            for r in demo.kills.iter_rows(named=True)
        ],
    )
)
```

For where the assets come from and how to manage the cache (`awpy.data`, the
`awpy get` CLI), see {doc}`visibility`.
