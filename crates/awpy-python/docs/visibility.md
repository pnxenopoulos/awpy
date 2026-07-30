# 👁️ Visibility & map data

Awpy can answer **line-of-sight** questions — is there a clear line between two
points on a map? — using the map's collision geometry. The geometry (and radar
images, nav meshes, and coordinate tables) come from the
[`awpy-data`](https://github.com/pnxenopoulos/awpy-data) project, which builds
them from a clean CS2 install and publishes them as GitHub Releases pinned to
the game's `ClientVersion`.

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

Construction loads the mesh and builds a bounding-volume hierarchy over its
triangles once, up front. Each query is then a fast ray cast, so **reuse a
single checker** for many queries rather than rebuilding it.

Points are `(x, y, z)` tuples (or lists) in **Hammer units, Z-up** — the same
frame as demo world positions, so the `*_x` / `*_y` / `*_z` columns from
`demo.kills`, `demo.grenades`, etc. can be passed straight in.

| Member | Type | Description |
| --- | --- | --- |
| `VisibilityChecker(source, *, version=None)` | | Load a map's mesh (or a `.mesh` file) and build its BVH. Raises `FileNotFoundError` / `ValueError`. |
| `is_visible(a, b)` | `bool` | Is the straight segment `a`→`b` unobstructed? |
| `is_occluded(a, b)` | `bool` | The complement of `is_visible`. |
| `triangle_count` | `int` | Triangles in the loaded mesh. |
| `path` | `Path \| None` | The file the mesh was loaded from. |

```python
# Was a kill made through a wall (a wallbang)? Compare the answer to reality.
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

The path helpers each download whatever archive they need the first time and
return a local `Path`:

```python
from awpy import data

data.mesh_path("de_inferno")            # -> .../geometry/de_inferno.mesh
data.nav_path("de_inferno")             # -> .../navs/de_inferno.nav
data.radar_path("de_nuke")              # -> .../radars/de_nuke.png
data.radar_path("de_nuke", lower=True)  # -> .../radars/de_nuke_lower.png
```

And the whole-release helpers return parsed JSON or lists:

```python
data.available_maps()          # ['ar_baggage', ..., 'de_vertigo']
data.map_data()["de_inferno"]  # {'pos_x': ..., 'scale': ..., ...}
data.manifest()["buildid"]     # Steam build the release was cut from
```

**Version.** Every accessor takes an optional `version=` — an integer
`ClientVersion` like `2000873`. Omit it to use the newest release already in
the cache; only an empty cache falls through to the latest GitHub release. No
network is involved once assets are cached, so analyses keep working offline
and don't shift releases under you mid-session:

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

`awpy get` is the explicit "check for updates" step: the accessors above never
replace a cached release on their own.
