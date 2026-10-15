# API reference

This page uses the installed package docstrings.
See {doc}`datasets` for columns, multipart queries, and {doc}`reference` for definitions.

## `Demo`

Open one demo or an ordered sequence of demo paths. Read datasets as Polars DataFrames.
Single-file construction maps the file and checks its header. Multipart construction
also checks round continuity and recording boundaries. Dataset access triggers decoding.
Results are cached; `Demo.load(...)` combines compatible requests.

```{eval-rst}
.. autoclass:: awpy.Demo
   :members:
   :undoc-members:
```

## `Events`

Read game events by name when no dedicated dataset is available.

```{eval-rst}
.. autoclass:: awpy._awpy.Events
   :members:
   :special-members: __getitem__, __contains__, __iter__, __len__
```

## `VisibilityChecker`

Check lines of sight against static collision geometry.
Reuse the checker to avoid rebuilding its spatial index. See {doc}`visibility`.

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

## awpy.map_control

Calculate map control from a demo. See
{doc}`map_control`.

```{eval-rst}
.. automodule:: awpy.map_control
   :members:
```
<!-- Omit :undoc-members: to avoid duplicate dataclass field documentation. -->

### `compute_map_control`

Calculate map control from a nav mesh and player positions.

```{eval-rst}
.. autofunction:: awpy._awpy.compute_map_control
```

## awpy.plot

Radar rendering, game-state frames, heatmaps, and GIFs. Requires the `plot`
extra — `pip install 'awpy[plot]'`. See {doc}`plot`.

```{eval-rst}
.. automodule:: awpy.plot
   :members:
   :undoc-members:
```

## awpy.data

Download and cache [awpy-data](https://github.com/pnxenopoulos/awpy-data) assets
under `~/.awpy/<version>/`. Set `AWPY_DATA_DIR` to change the root path.
Accessors use the newest cached release unless `version=` is set.
See {doc}`visibility`.

```{eval-rst}
.. automodule:: awpy.data
   :members:
```

## awpy.schema

List snapshot properties and common game events without parsing a demo.
Both catalogs are also available from `awpy`.
Use `demo.events.names` for the events in a specific demo.

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
