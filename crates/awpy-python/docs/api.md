# API reference

```python
from awpy import Demo

demo = Demo("match.dem")
demo.load("kills", "damages", "shots")
print(demo.header["map_name"])
print(demo.stats.select("name", "kills", "deaths", "assists", "adr", "kast"))
print(demo.snapshots(seconds=1.0))
```

This page uses the installed package docstrings.
See {doc}`datasets` for columns, multipart queries, and {doc}`reference` for definitions.

<a id="demo"></a>

## Parse CS2 recordings with Awpy Demo

Open one demo or an ordered sequence of demo paths. Read datasets as Polars DataFrames.
Single-file construction maps the file and checks its header. Multipart construction
also checks round continuity and recording boundaries. Dataset access triggers decoding.
Results are cached; `Demo.load(...)` combines compatible requests.

```{eval-rst}
.. autoclass:: awpy.Demo
   :members:
   :undoc-members:
```

<a id="events"></a>

## Read CS2 game events with Awpy Events

Read game events by name when no dedicated dataset is available.

```{eval-rst}
.. autoclass:: awpy._awpy.Events
   :members:
   :special-members: __getitem__, __contains__, __iter__, __len__
```

<a id="visibilitychecker"></a>

## Check CS2 collision geometry with Awpy VisibilityChecker

Check lines of sight against static collision geometry.
Reuse the checker to avoid rebuilding its spatial index. See {doc}`visibility`.

```{eval-rst}
.. autoclass:: awpy.VisibilityChecker
   :members:
   :undoc-members:
```

<a id="navmesh"></a>

## Query CS2 navigation meshes with Awpy NavMesh

A map's navigation mesh: the walkable areas and the graph connecting them. See
{doc}`nav`.

```{eval-rst}
.. autoclass:: awpy.NavMesh
   :members:
   :undoc-members:
   :special-members: __len__
```

<a id="awpymap_control"></a>
<a id="awpy-map-control"></a>

## Estimate CS2 map control with Awpy

Calculate map control from a demo. See
{doc}`map_control`.

```{eval-rst}
.. automodule:: awpy.map_control
   :members:
```
<!-- Omit :undoc-members: to avoid duplicate dataclass field documentation. -->

<a id="compute_map_control"></a>
<a id="compute-map-control"></a>

### Calculate Awpy map control from player observations

Calculate map control from a nav mesh and player positions.

```{eval-rst}
.. autofunction:: awpy._awpy.compute_map_control
```

<a id="awpyplot"></a>
<a id="awpy-plot"></a>

## Draw CS2 data with Awpy and matplotlib

Radar rendering, game-state frames, heatmaps, and GIFs. Requires the `plot`
extra — `pip install 'awpy[plot]'`. See {doc}`plot`.

```{eval-rst}
.. automodule:: awpy.plot
   :members:
   :undoc-members:
```

<a id="awpydata"></a>
<a id="awpy-data"></a>

## Download CS2 map assets with awpy.data

Download and cache [awpy-data](https://github.com/pnxenopoulos/awpy-data) assets
under `~/.awpy/<version>/`. Set `AWPY_DATA_DIR` to change the root path.
Accessors use the newest cached release unless `version=` is set.
See {doc}`visibility`.

```{eval-rst}
.. automodule:: awpy.data
   :members:
```

<a id="awpyschema"></a>
<a id="awpy-schema"></a>

## List Awpy snapshot fields and CS2 events

List snapshot properties and common game events without parsing a demo.
Both catalogs are also available from `awpy`.
Use `demo.events.names` for the events in a specific demo.

```{eval-rst}
.. autodata:: awpy.schema.SNAPSHOT_PROPERTIES
   :no-value:

.. autodata:: awpy.schema.GAME_EVENTS
   :no-value:
```

<a id="exceptions"></a>

## Handle Awpy parsing errors

```{eval-rst}
.. autoexception:: awpy.InvalidDemoError
```
