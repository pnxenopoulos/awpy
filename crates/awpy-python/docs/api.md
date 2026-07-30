# 📚 API reference

Every entry on this page is generated from the docstrings in the installed
package, so it always matches the version of Awpy you have. For the columns each
dataset returns, and worked examples of using them, see {doc}`datasets`; for how
the derived numbers are defined, see {doc}`reference`.

## `Demo`

The entry point: open a demo, then read datasets off it as
[Polars](https://pola.rs) DataFrames. Construction is cheap — it memory-maps the
file and checks its magic bytes — and decoding happens on first dataset access,
where the headline datasets are built together in one parallel pass and cached.

```{eval-rst}
.. autoclass:: awpy.Demo
   :members:
   :undoc-members:
```

## `Events`

The mapping returned by `Demo.events`: every game event in the demo, by name —
for the events without a curated dataset of their own.

```{eval-rst}
.. autoclass:: awpy._awpy.Events
   :members:
   :special-members: __getitem__, __contains__, __iter__, __len__
```

## `VisibilityChecker`

Line-of-sight queries against a map's collision geometry. Building the checker
loads the `.mesh` and builds a bounding-volume hierarchy once, so reuse a single
checker across many queries. See {doc}`visibility`.

```{eval-rst}
.. autoclass:: awpy.VisibilityChecker
   :members:
   :undoc-members:
```

## `NavMesh`

A map's navigation mesh: the walkable areas and the graph connecting them. See
{doc}`nav`.

```{eval-rst}
.. autoclass:: awpy.NavMesh
   :members:
   :undoc-members:
   :special-members: __len__
```

## `awpy.map_control`

How much of the map each team holds — the demo-oriented interface. See
{doc}`map_control`.

```{eval-rst}
.. automodule:: awpy.map_control
   :members:
```
<!-- No `:undoc-members:` here: MapControlParams documents its fields in the
     class docstring's `Attributes:` section, and pulling the bare dataclass
     fields in as well would document each one twice. -->


### `compute_map_control`

The low-level primitive the above is built on, for callers who already hold a nav
mesh and a list of player positions.

```{eval-rst}
.. autofunction:: awpy._awpy.compute_map_control
```

## `awpy.plot`

Radar rendering, game-state frames, heatmaps, and GIFs. Requires the `plot`
extra — `pip install 'awpy[plot]'`. See {doc}`plot`.

```{eval-rst}
.. automodule:: awpy.plot
   :members:
   :undoc-members:
```

## `awpy.data`

Downloads and caches CS2 map assets (collision meshes, nav meshes, radar images,
coordinate transforms) from the
[`awpy-data`](https://github.com/pnxenopoulos/awpy-data) releases, under
`$HOME/.awpy/<version>/` — override with `AWPY_DATA_DIR`. Resolution is
local-first, so once a release is cached no network access is involved. Every
accessor takes an optional `version=` (an integer ClientVersion); omit it for the
newest cached release. See {doc}`visibility`.

```{eval-rst}
.. automodule:: awpy.data
   :members:
```

## `awpy.schema`

Discoverable catalogs: which per-player features `snapshots` can return (mapped to
the engine properties they come from), and what the common game events are. Both
are plain dicts, so they are useful before you have parsed anything — the events a
*particular* demo contains are `demo.events.names`.

Both are re-exported at the top level, so `awpy.SNAPSHOT_PROPERTIES` and
`awpy.schema.SNAPSHOT_PROPERTIES` are the same object.

```{eval-rst}
.. autodata:: awpy.schema.SNAPSHOT_PROPERTIES
   :no-value:

.. autodata:: awpy.schema.GAME_EVENTS
   :no-value:
```

## Exceptions

```{eval-rst}
.. autoexception:: awpy.InvalidDemoError
```
