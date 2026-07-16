# 📈 Plotting

`awpy.plot` draws demo data on a map's **radar image** — the same 1024×1024
PNGs used by the in-game radar, fetched on demand by `awpy.data`. It needs
matplotlib, which ships as an optional extra:

```sh
pip install 'awpy[plot]'
```

Every function takes a map name, and — like the rest of awpy — an optional
`version=` to pin an [`awpy-data`](https://github.com/pnxenopoulos/awpy-data)
release (an integer `ClientVersion`); by default the newest cached release is
used, downloading the latest only when nothing is cached.

## Game state: `frame`

A *frame* is one moment of a round: players, and optionally the bomb. Each
player is a `plot.Player` — only `x`/`y` are required, everything else adds
detail:

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

`demo.snapshots(ticks=tick)` produces exactly these fields, so any moment of a real
demo is one comprehension away:

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

## Heatmaps: `heatmap`

Pass any iterable of world `(x, y)` or `(x, y, z)` rows — with Polars,
`.rows()` on a selection does it:

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

## Map control: `map_control`

Shade the map by which side controls each area at one tick, players and the
shaping occluders overlaid:

```python
from awpy import Demo, plot

demo = Demo("match.dem")

fig, ax = plot.map_control(demo, tick=29000, method="vision")
fig, ax = plot.map_control(demo, tick=29000, method="reachability")
```

Blue is CT, yellow is T, purple is contested; neutral is left unshaded, and the
legend shows each side's share of the map. `method` picks the model — `"vision"`
(line of sight, drawing the active smokes) or `"reachability"` (who reaches each
area first, drawing the active molotovs). Tune it with `params=` (a
`MapControlParams`), and see {doc}`map_control` for what the numbers mean.

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
everything drawn at full opacity on the level it's on:

```python
fig, (upper, lower) = plot.frame_levels("de_nuke", players, bomb=bomb)
fig, axes = plot.heatmap_levels("de_nuke", deaths, method="kde")
```

Both return `(fig, (ax_upper, ax_lower))`, and degrade gracefully to a single
panel on single-level maps — no need to special-case the map.

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

All of it is Hammer units, Z-up, straight from the demo dataframes — the same
frame as `VisibilityChecker`.
