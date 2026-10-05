# Visibility & map data

Use map collision geometry to check whether a straight segment is blocked.
[awpy-data](https://github.com/pnxenopoulos/awpy-data) supplies collision meshes,
nav meshes, radar images, and coordinate tables by game `ClientVersion`.

## `VisibilityChecker`

```python
from awpy import VisibilityChecker

vc = VisibilityChecker("de_inferno")

a = (1258.04, 455.47, 181.22)   # a world position (Hammer units, Z-up)
b = (-158.62, 819.09, 103.73)
vc.is_visible(a, b)             # -> True  (clear line)
vc.is_visible((1398.43, 705.44, 192.33), b)  # -> False (a wall is in the way)
```

The constructor takes a map name or a mesh file:

```python
VisibilityChecker("de_inferno")                    # newest release cached under ~/.awpy
                                                   # (downloads the latest if none is cached)
VisibilityChecker("de_inferno", version=2000873)   # pin an awpy-data release
VisibilityChecker("path/to/de_inferno.mesh")       # load a specific .mesh file
```

A string counts as a file path when it ends in `.mesh` or contains a path
separator; a `pathlib.Path` always does. Anything else is treated as a map
name and resolved through `awpy.data.mesh_path`.

Reuse a checker to avoid loading the mesh and rebuilding its spatial index.

Points are `(x, y, z)` tuples or lists in Hammer units, with Z vertical.
The checker uses static geometry. It does not model smokes, moving doors,
or bullet penetration. Player positions are not eye positions.

| Member | Type | Description |
| --- | --- | --- |
| `VisibilityChecker(source, *, version=None)` | | Load a map's mesh (or a `.mesh` file) and build its BVH. Raises `FileNotFoundError` / `ValueError`. |
| `is_visible(a, b)` | `bool` | Is the straight segment `a`→`b` unobstructed? |
| `is_occluded(a, b)` | `bool` | The complement of `is_visible`. |
| `triangle_count` | `int` | Triangles in the loaded mesh. |
| `path` | `Path \| None` | The file the mesh was loaded from. |

```python
# Check the segment between recorded player positions.
kills = demo.kills
row = kills.row(0, named=True)
attacker = (row["attacker_x"], row["attacker_y"], row["attacker_z"])
victim = (row["victim_x"], row["victim_y"], row["victim_z"])
had_los = vc.is_visible(attacker, victim)
```

## Fetching assets: awpy.data

`awpy.data` downloads assets on demand and caches them under
`$HOME/.awpy/<version>/` (override the root with the `AWPY_DATA_DIR`
environment variable):

```
$HOME/.awpy/2000873/
    manifest.json          version identifiers + per-file checksums
    map_data.json          per-map world->radar transform
    radars/<map>.png       radar image (+ <map>_lower.png for Nuke/Vertigo/Train)
    navs/<map>.nav         nav mesh
    geometry/<map>.mesh    collision mesh for VisibilityChecker
```

Path helpers download missing archives and return local paths:

```python
from awpy import data

data.mesh_path("de_inferno")            # -> .../geometry/de_inferno.mesh
data.nav_path("de_inferno")             # -> .../navs/de_inferno.nav
data.radar_path("de_nuke")              # -> .../radars/de_nuke.png
data.radar_path("de_nuke", lower=True)  # -> .../radars/de_nuke_lower.png
```

Read release metadata:

```python
data.available_maps()          # ['ar_baggage', ..., 'de_vertigo']
data.map_data()["de_inferno"]  # {'pos_x': ..., 'scale': ..., ...}
data.manifest()["buildid"]     # Steam build the release was cut from
```

Set `version=` to select a `ClientVersion`.
Without it, accessors use the newest cached release.
An empty cache uses the latest GitHub release.
Cached assets work offline.

```python
data.mesh_path("de_inferno", version=2000873)
```

**Managing the cache.**

```python
data.update()         # download every asset for the latest release
data.update(2000873)  # ... or a specific one
data.clear(2000873)   # delete one release's cache
data.clear()          # delete the whole cache
```

## Command line: `awpy get`

The [`awpy` command](cli.md) also manages the asset cache:

```sh
awpy get             # download the latest release
awpy get 2000873     # ... or a specific one (--force to re-download)
awpy versions        # cached releases, and whether a newer one exists
awpy maps            # maps available in a release
awpy clear 2000873   # delete one cached release (--all for everything)
```

Use `awpy get` to check for updates. Accessors do not replace cached releases.
