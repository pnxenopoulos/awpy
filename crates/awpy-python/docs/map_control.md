# Map control

Map control labels each {doc}`nav area <nav>` as `"ct"`, `"t"`,
`"contested"` (both sides), or `"neutral"` (neither side).
Summary fractions are weighted by area size. `net_control = ct - t`.

Choose a model:

- `raycast`: line of sight in any direction, regardless of player yaw.
- `vision`: line of sight within the horizontal field of view (90° by default).
- `reachability`: the side with the shortest travel distance over the nav graph.
  Similar distances are contested; unreachable areas are neutral.

Smokes block line-of-sight rays. Flash state and `flash_threshold` exclude
blinded players from those models. Fires block paths in the reachability model.

All three need the map's `.nav` (from `awpy.data`); the two line-of-sight models
also need the collision `.mesh`. Both are fetched on demand.

The vision model uses yaw and ignores pitch.
Missing yaw or `fov >= 360` removes the field-of-view limit for that player.

```{figure} img/map-control-cone.webp
:alt: One player on Inferno with their 90 degree view cone drawn; grey marks everything raycast sees, cyan the subset inside the cone
:width: 100%

Grey areas have line of sight. Cyan areas also fall inside the player's view cone.
Walls and smokes can block areas within the cone.
Team results combine the visible areas of all eligible players.
```

## Time series: `map_control`

Returns one summary row per selected tick.
Use {meth}`Demo.snapshots` selectors. Prefer `seconds=1` or event ticks
to reduce computation.

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

Returns one row per nav area at one tick, for analysis or {func}`awpy.plot.map_control`.

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

Compare the models at the same tick:

```{figure} img/map-control-raycast.webp
:alt: Inferno shaded by raycast map control, with most of the map unshaded and CT and T holding their sightlines
:width: 100%

`raycast` includes sightlines in all directions. Unseen areas are neutral.
```

```{figure} img/map-control-vision.webp
:alt: The same Inferno tick under field-of-view vision, holding noticeably less of the map than raycast
:width: 100%

`vision` limits each player to a horizontal 90° field of view.
```

```{figure} img/map-control-reachability.webp
:alt: The same Inferno tick shaded by reachability, with CT at 56 percent and T at 42 percent and a thin contested boundary
:width: 100%

`reachability` compares travel distances. Purple areas have similar distances
from both sides.
```

Use raycast for possible sightlines, vision for view-direction limits,
and reachability for travel distance.

## Tuning: `MapControlParams`

Pass `params=MapControlParams(...)` to change the defaults.
"Line of sight" below means both `raycast` and `vision`.

```python
from awpy.map_control import MapControlParams

params = MapControlParams(max_distance=2500.0, contest_margin=300.0)
ts = mc.map_control(demo, method="vision", seconds=1, params=params)
```

| Parameter | Default | Applies to | Meaning |
| --- | --- | --- | --- |
| `eye_height` | `64.0` | line of sight | Standing ray origin height above the feet. |
| `crouch_eye_height` | `46.0` | line of sight | Eye height when crouched. |
| `target_height` | `46.0` | line of sight | Ray endpoint height above an area's floor. |
| `max_distance` | `None` | line of sight | Optional vision-range cap in Hammer units; `None` is unbounded. |
| `contest_margin` | `200.0` | reachability | Maximum travel-distance difference for contested areas. |
| `fov` | `90.0` | vision only | Horizontal field of view in degrees; an area counts only within `fov / 2` of where the player looks. `360` or more removes the limit. |
| `smoke_radius` | `144.0` | line of sight | Radius of a smoke cloud that blocks vision. |
| `smoke_height` | `60.0` | line of sight | Height of the smoke sphere center above the landing point. |
| `fire_radius` | `150.0` | reachability | Blocked ground radius around a fire. |
| `flash_threshold` | `1.0` | line of sight | A currently flashing player projects no vision when the replicated onset duration exceeds this value. This filters short partial flashes. |

## Notes & limitations

- Each side's visible area set in `vision` is a subset of its `raycast` set.
  Exclusive `ct` and `t` fractions need not decrease: a contested area can
  become exclusive when the other side loses sight of it.
- Dead players do not contribute. Blinded players can contribute to reachability.
- Smokes affect line of sight; fires affect reachability.
- Vision ignores pitch. These models estimate control, not exact player perception.
- Coordinates use Hammer units, with Z vertical.

For the lower-level API, see `awpy._awpy.compute_map_control`.
