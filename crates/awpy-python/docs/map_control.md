# 🗺️ Map control

**Map control** turns a snapshot of player positions into a partition of the
map's {doc}`navigation mesh <nav>`: every walkable area is labelled `"ct"`,
`"t"`, `"contested"` (both teams hold it), or `"neutral"` (neither does).
Aggregated and weighted by area size, that's a single, interpretable *fraction
of the map* each side holds — and its signed difference, `net_control`, is a
compact momentum series you can plot across a round.

Two models are offered, because "control" means two different things:

- **`method="vision"`** — *what a team can see.* An area is held by a side if any
  living, un-blinded player has line of sight to it (a ray through the collision
  mesh, the same one {doc}`VisibilityChecker <visibility>` uses). Active **smokes**
  block the rays that cross them; a **flashed** player projects no vision.
- **`method="reachability"`** — *what space a team can take first.* Whichever
  side's nearest player can travel to an area first (over the nav graph) holds it;
  a near-tie is contested, and unreachable space is neutral. Burning **molotovs**
  deny the ground under them, so paths route around it.

Both need the map's `.nav` (from `awpy.data`); vision also needs the collision
`.mesh`. Both are fetched on demand.

## Time series: `map_control`

One row of summary fractions per selected tick. Ticks are chosen exactly as in
{meth}`Demo.snapshots` — since this samples the whole demo, prefer a coarse
cadence (`seconds=1`) or event ticks over every single tick.

```python
from awpy import Demo
from awpy import map_control as mc

demo = Demo("match.dem")

ts = mc.map_control(demo, method="vision", seconds=1)
# shape: (…, 7)
# ┌───────┬────────┬──────────┬──────────┬───────────┬──────────┬─────────────┐
# │ tick  ┆ method ┆ ct       ┆ t        ┆ contested ┆ neutral  ┆ net_control │
# ╞═══════╪════════╪══════════╪══════════╪═══════════╪══════════╪═════════════╡
# │ 54144 ┆ vision ┆ 0.166045 ┆ 0.048025 ┆ 0.0       ┆ 0.785929 ┆ 0.118020    │
# │ …     ┆ …      ┆ …        ┆ …        ┆ …         ┆ …        ┆ …           │
```

`ct` / `t` / `contested` / `neutral` are the size-weighted fraction of the map in
each bucket (they sum to 1); `net_control = ct - t`.

## Per area: `map_control_at`

One row **per nav area** at a single tick — the shape {func}`awpy.plot.map_control`
draws, and what you'd join back onto the mesh for your own analysis.

```python
areas = mc.map_control_at(demo, tick=29000, method="reachability")
# columns: area_id, control, ct, t, centroid_x, centroid_y, centroid_z, size
```

`control` is the area's label; `ct` / `t` say whether that side holds it (alone
or contested). The `centroid_*` / `size` come from the nav mesh so you can weight
or place each area without a second lookup.

## Visualizing: `plot.map_control`

Shade the map by who controls each area, with players and the shaping occluders
(smokes for vision, molotovs for reachability) overlaid:

```python
from awpy import plot

fig, ax = plot.map_control(demo, tick=29000, method="vision")
fig.savefig("vision.png")

fig, ax = plot.map_control(demo, tick=29000, method="reachability")
```

Blue is CT, yellow is T, purple is contested; neutral is left unshaded. The
legend shows each side's share of the map. Requires the plotting extra
(`pip install 'awpy[plot]'`).

## Tuning: `MapControlParams`

Every knob has a sane default; override any of them with a `MapControlParams`
and pass `params=` to any of the functions above.

```python
from awpy.map_control import MapControlParams

params = MapControlParams(max_distance=2500.0, contest_margin=300.0)
ts = mc.map_control(demo, method="vision", seconds=1, params=params)
```

| Parameter | Default | Applies to | Meaning |
| --- | --- | --- | --- |
| `eye_height` | `64.0` | vision | Standing eye height above the feet — where rays start. |
| `crouch_eye_height` | `46.0` | vision | Eye height when crouched. |
| `target_height` | `46.0` | vision | Height above an area's floor the rays aim at (a player's chest, not the bare floor). |
| `max_distance` | `None` | vision | Optional vision-range cap in Hammer units; `None` is unbounded. |
| `contest_margin` | `200.0` | reachability | Travel-distance tie band — areas whose two sides' distances differ by ≤ this are contested. |
| `smoke_radius` | `144.0` | vision | Radius of a smoke cloud that blocks vision. |
| `smoke_height` | `60.0` | vision | How far above its landing point a smoke's blocking sphere is centred. |
| `fire_radius` | `150.0` | reachability | Radius around a molotov within which the ground is denied. |
| `flash_threshold` | `1.0` | vision | A player is blind (projects no vision) while more than this many seconds of flash remain. |

## Notes & limitations

- **Vision is sparse, reachability is dense.** Vision typically leaves most of
  the map neutral (unseen) with a little contested overlap where sightlines meet;
  reachability partitions almost everything, with a contested frontier where the
  teams meet. They answer different questions — compute both from one snapshot and
  compare.
- **Dead players don't contribute** (to either model); **blinded players** hold
  space (reachability) but see nothing (vision).
- **Smokes affect vision, molotovs affect reachability** — not the reverse: the
  static collision mesh can't be occluded by a molotov, and a smoke doesn't stop
  you walking through it.
- All coordinates are **Hammer units, Z-up**, the same frame as the demo world
  positions and {doc}`nav <nav>` / {doc}`visibility <visibility>`.

For the low-level primitive these build on, see `awpy._awpy.compute_map_control`.
```
