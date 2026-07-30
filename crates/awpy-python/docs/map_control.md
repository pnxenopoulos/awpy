# 🗺️ Map control

**Map control** turns a snapshot of player positions into a partition of the
map's {doc}`navigation mesh <nav>`: every walkable area is labelled `"ct"`,
`"t"`, `"contested"` (both teams hold it), or `"neutral"` (neither does).
Aggregated and weighted by area size, that's a single, interpretable *fraction
of the map* each side holds — and its signed difference, `net_control`, is a
compact momentum series you can plot across a round.

Three models are offered, because "control" means more than one thing:

- **`method="raycast"`** — *what a team could see.* An area is held by a side if
  any living, un-blinded player has line of sight to it **in any direction** (a ray
  through the collision mesh, the same one {doc}`VisibilityChecker <visibility>`
  uses). Active **smokes** block the rays that cross them; a **flashed** player
  projects no vision. This is the "what if they spun on the spot" reading — it
  ignores where players are actually looking.
- **`method="vision"`** — *what a team can actually see right now.* The same rays,
  narrowed to each player's **field of view**: within `fov / 2` degrees of where
  they are looking, defaulting to CS2's own **90°**. A player watching one angle no
  longer holds the space behind them, so this reports substantially less control
  than `"raycast"`.
- **`method="reachability"`** — *what space a team can take first.* Whichever
  side's nearest player can travel to an area first (over the nav graph) holds it;
  a near-tie is contested, and unreachable space is neutral. Burning **molotovs**
  deny the ground under them, so paths route around it.

All three need the map's `.nav` (from `awpy.data`); the two line-of-sight models
also need the collision `.mesh`. Both are fetched on demand.

The field-of-view cone is **horizontal** — it compares the player's yaw against the
bearing to each area and ignores pitch, since a player's vertical view depends on
their aspect ratio while yaw is what determines map coverage. A player whose yaw
the snapshot can't resolve has no direction to test, so no limit is applied to
them; setting `fov=360` removes the limit entirely, making `"vision"` identical to
`"raycast"`.

```{figure} img/map-control-cone.webp
:alt: One player on Inferno with their 90 degree view cone drawn; grey marks everything raycast sees, cyan the subset inside the cone
:width: 100%

What `"vision"` does, isolated to **one** player. Grey is everything `"raycast"`
gives them — every sightline, in any direction. Cyan is the `"vision"` subset. The
solid line is their yaw and the dashed lines are the two 45° cone edges, so the
shading can be checked against them by eye: nothing cyan falls outside.

Most of the cone is still unshaded, because a cone is only the *first* filter —
walls and smokes cut the rest. And note the team-level figures further down shade
the **union of five such cones**, one per player, each pointing somewhere different;
that is why they look scattered rather than cone-shaped.
```

## Time series: `map_control`

One row of summary fractions per selected tick. Ticks are chosen exactly as in
{meth}`Demo.snapshots` — since this samples the whole demo, prefer a coarse
cadence (`seconds=1`) or event ticks over every single tick.

```python
from awpy import Demo
from awpy import map_control as mc

demo = Demo("match.dem")

ts = mc.map_control(demo, method="raycast", seconds=1)
# shape: (…, 7)
# ┌───────┬─────────┬──────────┬──────────┬───────────┬──────────┬─────────────┐
# │ tick  ┆ method  ┆ ct       ┆ t        ┆ contested ┆ neutral  ┆ net_control │
# ╞═══════╪═════════╪══════════╪══════════╪═══════════╪══════════╪═════════════╡
# │ 54144 ┆ raycast ┆ 0.166045 ┆ 0.048025 ┆ 0.0       ┆ 0.785929 ┆ 0.118020    │
# │ …     ┆ …       ┆ …        ┆ …        ┆ …         ┆ …        ┆ …           │
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

## Visualizing: plot.map_control

Shade the map by who controls each area, with players and the shaping occluders
(smokes for vision, molotovs for reachability) overlaid:

```python
from awpy import plot

fig, ax = plot.map_control(demo, tick=29000, method="vision")
fig.savefig("vision.png")

fig, ax = plot.map_control(demo, tick=29000, method="raycast")
fig, ax = plot.map_control(demo, tick=29000, method="reachability")
```

Blue is CT, yellow is T, purple is contested; neutral is left unshaded. The
legend shows each side's share of the map. Requires the plotting extra
(`pip install 'awpy[plot]'`).

The methods answer different questions, and drawing the same tick each way is the
quickest way to see it:

```{figure} img/map-control-raycast.webp
:alt: Inferno shaded by raycast map control, with most of the map unshaded and CT and T holding their sightlines
:width: 100%

`method="raycast"` — every sightline a player has, in any direction. Most of the
map is still neutral, because most of it is not in anyone's line of sight from
where they stand.
```

```{figure} img/map-control-vision.webp
:alt: The same Inferno tick under field-of-view vision, holding noticeably less of the map than raycast
:width: 100%

`method="vision"` — the same rays, clipped to each player's 90° field of view.
Strictly a subset of the raycast picture: only the arc each player is actually
watching counts.
```

```{figure} img/map-control-reachability.webp
:alt: The same Inferno tick shaded by reachability, with CT at 56 percent and T at 42 percent and a thin contested boundary
:width: 100%

`method="reachability"` — who gets there first. Nearly every area belongs to
somebody, and the thin purple seam is the frontier where the two sides meet.
```

Same tick, same players, three answers. The two line-of-sight models leave most
of the map neutral and vision is always a subset of raycast, while reachability
partitions nearly everything. None is more correct than the others — pick the one
that matches your question. Raycast suits "what could they see from there", vision
suits "what are they actually watching", and reachability suits "whose territory is
this".

## Tuning: `MapControlParams`

Every knob has a sane default; override any of them with a `MapControlParams`
and pass `params=` to any of the functions above. "Line of sight" below means
both `"raycast"` and `"vision"`.

```python
from awpy.map_control import MapControlParams

params = MapControlParams(max_distance=2500.0, contest_margin=300.0)
ts = mc.map_control(demo, method="vision", seconds=1, params=params)
```

| Parameter | Default | Applies to | Meaning |
| --- | --- | --- | --- |
| `eye_height` | `64.0` | line of sight | Standing eye height above the feet — where rays start. |
| `crouch_eye_height` | `46.0` | line of sight | Eye height when crouched. |
| `target_height` | `46.0` | line of sight | Height above an area's floor the rays aim at (a player's chest, not the bare floor). |
| `max_distance` | `None` | line of sight | Optional vision-range cap in Hammer units; `None` is unbounded. |
| `contest_margin` | `200.0` | reachability | Travel-distance tie band — areas whose two sides' distances differ by ≤ this are contested. |
| `fov` | `90.0` | vision only | Horizontal field of view in degrees; an area counts only within `fov / 2` of where the player looks. `360` or more removes the limit. |
| `smoke_radius` | `144.0` | line of sight | Radius of a smoke cloud that blocks vision. |
| `smoke_height` | `60.0` | line of sight | How far above its landing point a smoke's blocking sphere is centred. |
| `fire_radius` | `150.0` | reachability | Radius around a molotov within which the ground is denied. |
| `flash_threshold` | `1.0` | line of sight | A player is blind (projects no vision) while more than this many seconds of flash remain. |

## Notes & limitations

- **Line of sight is sparse, reachability is dense.** Raycast and vision typically
  leave most of the map neutral (unseen) with a little contested overlap where
  sightlines meet; reachability partitions almost everything, with a contested
  frontier where the teams meet. They answer different questions — compute them from
  one snapshot and compare.
- **Vision ⊆ raycast, always.** The field-of-view cone can only remove areas, never
  add them, so `vision` fractions are bounded above by `raycast` on the same tick.
  That makes their difference a usable quantity in itself: how much of what a team
  *could* see they were actually looking at.
- **Dead players don't contribute** (to either model); **blinded players** hold
  space (reachability) but see nothing (vision).
- **Smokes affect the line-of-sight models, molotovs affect reachability** — not
  the reverse: the static collision mesh can't be occluded by a molotov, and a smoke
  doesn't stop you walking through it.
- **The FOV cone is horizontal.** Pitch is ignored, so a player looking at the floor
  or the sky still "sees" their arc. Yaw is what determines map coverage; vertical
  view depends on aspect ratio.
- All coordinates are **Hammer units, Z-up**, the same frame as the demo world
  positions and {doc}`nav <nav>` / {doc}`visibility <visibility>`.

For the low-level primitive these build on, see `awpy._awpy.compute_map_control`.
```
