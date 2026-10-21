# Navigation meshes

```python
from awpy import NavMesh

nav = NavMesh("de_dust2")
route = nav.find_path((-680.0, 1500.0, 0.0), (1200.0, 2400.0, 0.0))
print(route)
print(nav.areas)
```

A navigation mesh divides walkable space into connected polygonal areas.
Use `NavMesh` to locate a point or find a route.
[awpy-data](https://github.com/pnxenopoulos/awpy-data) supplies CS2 `.nav` files.

```{figure} img/nav-mesh.webp
:alt: Dust 2's navigation mesh drawn over its radar image, with 2242 walkable areas outlined in amber
:width: 100%

Dust 2 nav areas, drawn with {func}`awpy.plot.nav`.
```

<a id="navmesh"></a>

## Load CS2 navigation meshes with Awpy NavMesh

```python
from awpy import NavMesh

nav = NavMesh("de_dust2")
print(nav.find_area((-1500.0, 900.0, 60.0)))
print(nav.find_path((-680.0, 1500.0, 0.0), (1200.0, 2400.0, 0.0)))
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

Points use `(x, y, z)` in Hammer units, with Z vertical.
`find_area` returns a numeric `area_id`.

<a id="areas"></a>

### Read Awpy navigation area geometry

`nav.areas` has one row per area:

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

<a id="queries"></a>

### Find CS2 areas and paths with Awpy NavMesh

```python
start = (-680.0, 1500.0, 0.0)
end = (1200.0, 2400.0, 0.0)
area = nav.find_area(start)
if area is not None:
    print(nav.neighbors(area))
print(nav.find_path(start, end))
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
nav.find_path(start, end, weight="distance")  # default: 3D distance between centroids
nav.find_path(start, end, weight="hops")      # fewest areas
nav.find_path(start, end, weight="size")      # sum of area sizes; routes away from large areas
```

Draw a route with {func}`awpy.plot.nav`:

```python
from awpy.plot import nav as plot_nav

route = nav.find_path((-680.0, 1500.0, 0.0), (1200.0, 2400.0, 0.0))
fig, ax = plot_nav("de_dust2", highlight=route)
```

```{figure} img/nav-path.webp
:alt: The same Dust 2 nav mesh with a 70-area route highlighted in cyan, running from T spawn through mid toward the A site
:width: 100%

Use `highlight=` to draw a route or another set of area IDs.
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

<a id="example-tag-every-kill-with-its-area"></a>

### Assign CS2 kills to Awpy navigation areas

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

See {doc}`visibility` for assets and cache management.
