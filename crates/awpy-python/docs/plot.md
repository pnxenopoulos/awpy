# Plotting

Use `awpy.plot` to draw demo data on radar images.
Install the plotting dependencies:

```sh
pip install 'awpy[plot]'
```

Functions take a map name and an optional `version=`.
Assets use the newest cached release, or the latest release if none is cached.

## Game state: `frame`

Use `plot.Player` for each player. Only `x` and `y` are required:

```python
from awpy import plot

players = [
    plot.Player(x=-158.6, y=819.1, z=103.7, side="ct", hp=87, armor=50, label="ct1"),
    plot.Player(x=1258.0, y=455.5, z=181.2, side="t", yaw=135.0),
    plot.Player(x=800.0, y=600.0, z=150.0, side="t", hp=0),   # dead -> dim cross
]
fig, ax = plot.frame("de_inferno", players, bomb=(200.0, 480.0, 90.0))
fig.savefig("frame.png")
```

- `side` colors the marker — `"t"` / `"ct"`, or the demo dataframes'
  `"terrorist"` / `"counter-terrorist"`, any case. `color=` overrides it.
- `hp` / `armor` draw bars under the marker; `hp=0` renders the player dead.
- `yaw` (degrees, 0 = +x, counter-clockwise — the demo's eye-angle yaw) draws
  a view-direction tick.
- `label` prints text below the marker.

Convert snapshot rows to player markers:

```python
from awpy import Demo, plot

demo = Demo("match.dem")
snap = demo.snapshots(ticks=29000)
players = [
    plot.Player(x=r["x"], y=r["y"], z=r["z"], yaw=r["yaw"], hp=r["health"],
                armor=r["armor"], side=r["side"], label=r["name"])
    for r in snap.iter_rows(named=True)
]
fig, ax = plot.frame(demo.header["map_name"], players)
```

```{figure} img/plot-frame.webp
:alt: Inferno radar with ten player markers, each labelled and carrying green health and grey armor bars
:width: 100%

Inferno player markers with names, view directions, health, and armor.
```

## Heatmaps: `heatmap`

Pass world `(x, y)` or `(x, y, z)` rows:

```python
from awpy import Demo, plot

kills = Demo("match.dem").kills
deaths = kills.select(["victim_x", "victim_y", "victim_z"]).rows()

fig, ax = plot.heatmap("de_inferno", deaths, method="kde")
fig, ax = plot.heatmap("de_inferno", deaths, method="hex", bins=36)
fig, ax = plot.heatmap("de_inferno", deaths, method="hist", bins=64, cmap="viridis")
```

`method` is `"hex"` (hexagonal binning), `"hist"` (square binning), or
`"kde"` (gaussian-smoothed density; tune the smoothing radius in radar pixels
with `bandwidth=`). `bins` sets the grid resolution, `cmap` any matplotlib
colormap, `alpha` the overlay opacity. Empty cells stay transparent, so the
radar shows through.

```{figure} img/plot-heatmap.webp
:alt: Inferno radar overlaid with a smoothed density map of death locations, brightest at banana and the apartments
:width: 100%

Death locations from one match, drawn with `method="kde"`.
```

## Map control: `map_control`

Shade the map by which side controls each area at one tick, players and the
shaping occluders overlaid:

```python
from awpy import Demo, plot

demo = Demo("match.dem")

fig, ax = plot.map_control(demo, tick=29000, method="vision")
fig, ax = plot.map_control(demo, tick=29000, method="raycast")
fig, ax = plot.map_control(demo, tick=29000, method="reachability")
```

Blue is CT, yellow is T, purple is contested; neutral is left unshaded, and the
legend shows each side's share of the map. `method` picks the model —
`"raycast"` (line of sight in any direction), `"vision"` (the same, clipped to each
player's 90° field of view), or `"reachability"` (who reaches each area first). The
first two draw the active smokes, reachability the active molotovs. Tune it with
`params=` (a `MapControlParams`), and see {doc}`map_control` for what the numbers
mean.

```{figure} img/map-control-reachability.webp
:alt: Inferno shaded blue for CT and yellow for T with a thin purple contested seam, players and a legend overlaid
:width: 100%

`method="reachability"` on Inferno. {doc}`map_control` shows this same tick under
all three models — the raycast, vision, and reachability pictures differ a lot.
```

## Multi-level maps

Nuke, Vertigo, Train, and Baggage have two radar images. Pass `lower=True` to
draw the lower level; points are matched to their level by altitude, using
the vertical sections published in `map_data.json`:

```python
fig, ax = plot.frame("de_nuke", players, lower=True)   # ramp room & B site
plot.is_lower_level("de_nuke", z=-600.0)               # -> True
plot.has_lower_level("de_nuke")                        # -> True
```

On a single radar, players on the *other* level are dimmed (`off_level_alpha=`,
`0` hides them) and off-level heatmap points are skipped with a warning. When a
game state spans both levels, use the `_levels` variants — one panel per level,
each point at full opacity on its level:

```python
fig, (upper, lower) = plot.frame_levels("de_nuke", players, bomb=bomb)
fig, axes = plot.heatmap_levels("de_nuke", deaths, method="kde")
```

Both return `(fig, (ax_upper, ax_lower))` for two-level maps.
Single-level maps return one panel.

```{figure} img/plot-frame-levels.webp
:alt: Two Nuke radar panels labelled upper and lower, with blue CT markers on the upper panel and yellow T markers on the lower
:width: 100%

`frame_levels` on Nuke, with positions sampled from nav areas.
Altitude determines each player's panel.
```

```{figure} img/plot-heatmap-levels.webp
:alt: The same two Nuke panels with a hexagonal density overlay on each, denser on the upper level
:width: 100%

`heatmap_levels` groups points by level.
```

## Animation: `gif`

Render a sequence of frames to an animated GIF — each entry is a list of
players, or a dict of `frame` keyword arguments:

```python
plot.gif(
    "de_inferno",
    [
        [plot.Player(x=0, y=0, side="t")],
        {"players": [plot.Player(x=50, y=20, side="t")], "bomb": (200, 480, 90)},
    ],
    "round.gif",
    fps=2,
)
```

## Navigation meshes: `nav`

Draw nav areas and highlight selected area IDs:

```python
from awpy import NavMesh, plot

fig, ax = plot.nav("de_dust2")

mesh = NavMesh("de_dust2")
route = mesh.find_path((-680.0, 1500.0, 0.0), (1200.0, 2400.0, 0.0))
fig, ax = plot.nav("de_dust2", highlight=route)
```

```{figure} img/nav-path.webp
:alt: Dust 2's nav mesh in amber with a 70-area route highlighted in cyan
:width: 100%

`highlight=` takes any iterable of area ids. See {doc}`nav` for the mesh itself.
```

Areas are filtered to the level being drawn, so a multi-level map needs one call
per level (`lower=True`). `edge=False` drops the outlines for a flatter fill, and
`legend=False` removes the area count.

## Building blocks

`radar` draws the bare map and returns `(fig, ax)`; every other function
accepts `ax=` so you can layer plots — e.g. a heatmap under a frame, or your
own matplotlib artists on top. Positions are drawn in **radar pixel
coordinates**, and the transforms are public:

```python
fig, ax = plot.radar("de_inferno", version=2000873)
plot.heatmap("de_inferno", deaths, method="kde", ax=ax)
plot.frame("de_inferno", players, ax=ax)

px, py = plot.world_to_pixel("de_inferno", (1258.0, 455.5))
x, y = plot.pixel_to_world("de_inferno", (px, py))
```

```{figure} img/plot-radar.webp
:alt: The bare Dust 2 radar image with no overlays
:width: 60%
:align: center

The radar image without overlays.
```

Input positions use Hammer units, with Z vertical.

---

Figures are generated by `scripts/build_docs_images.py` and stored in the repository.
Run the script and commit updated images when plot appearance changes.
