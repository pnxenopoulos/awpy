"""Map control: how much of the map each team holds, tick by tick.

*Map control* turns a snapshot of player positions into a partition of the
map's navigation mesh — every walkable area is labelled ``"ct"``, ``"t"``,
``"contested"`` (both teams hold it), or ``"neutral"`` (neither does) — and
aggregates that, weighted by area size, into a single fraction of the map held
by each side. Three models are offered, because "control" means more than one
thing:

- ``method="raycast"`` — *what a team could see.* An area is held by a side if any
  living, un-blinded player on it has line of sight to the area (a ray through
  the map's collision mesh) **in any direction**. Active smokes block the rays
  that cross them, and a flashed player projects no vision.

- ``method="vision"`` — *what a team can actually see.* The same rays, narrowed to
  each player's **field of view**: within ``fov / 2`` degrees of where they are
  looking (default 90°, CS2's own FOV). A player watching one angle no longer
  holds the space behind them, so this reports notably less control than
  ``"raycast"``.

- ``method="reachability"`` — *what space a team can take first.* Whichever
  side's nearest player can travel to an area first (over the nav graph) holds
  it; a near-tie is contested and unreachable space is neutral. Burning
  molotovs deny the ground under them, so paths route around it.

Two entry points, sharing one per-tick computation:

- :func:`map_control` returns a **time series** — one row of summary fractions
  per selected tick (choose ticks exactly as with :meth:`awpy.Demo.snapshots`).
- :func:`map_control_at` returns the **per-area** labels at a single tick, which
  is what :func:`awpy.plot.map_control` draws.

::

    from awpy import Demo
    from awpy import map_control as mc

    demo = Demo("match.dem")
    ts = mc.map_control(demo, method="vision", seconds=1)   # a momentum series
    areas = mc.map_control_at(demo, tick=29000, method="reachability")

Requires the map's ``.nav`` (all three models) and ``.mesh`` (the line-of-sight
models, ``"raycast"`` and ``"vision"``), fetched on demand by :mod:`awpy.data`.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

import polars as pl

from awpy._awpy import NavMesh, VisibilityChecker, compute_map_control

if TYPE_CHECKING:
    from awpy import Demo

__all__ = [
    "LINE_OF_SIGHT_METHODS",
    "MapControlParams",
    "Method",
    "map_control",
    "map_control_at",
]

Method = Literal["raycast", "vision", "reachability"]

#: Methods that cast rays through the collision mesh, and so need a
#: :class:`~awpy.VisibilityChecker`.
LINE_OF_SIGHT_METHODS: frozenset[str] = frozenset({"raycast", "vision"})

#: Summary columns of a :func:`map_control` time series (besides ``tick`` /
#: ``method``): the size-weighted fraction of the map in each bucket, and the
#: signed CT-minus-T difference.
_SUMMARY_COLUMNS = ("ct", "t", "contested", "neutral", "net_control")


@dataclass(frozen=True)
class MapControlParams:
    """Knobs for the map-control models (all optional; the defaults are sane).

    Grouped by what they affect: *vision geometry* (the first four, in Hammer
    units), *reachability* (``contest_margin``), and the *dynamic occluders* that
    smokes, molotovs, and flashes create.

    Attributes:
        eye_height: Standing eye height above the feet — where vision rays start.
        crouch_eye_height: Eye height when crouched.
        target_height: Height above an area's floor that vision aims at, modelling
            "would I see a player standing here" rather than the bare floor.
        max_distance: Optional cap on vision range; ``None`` is unbounded.
        contest_margin: Travel-distance tie band — areas whose two sides' travel
            distances differ by no more than this are contested.
        fov: Horizontal field of view in degrees for ``method="vision"`` — an area
            counts only within ``fov / 2`` either side of where the player looks.
            The default matches CS2's own FOV; ``360`` or more removes the limit,
            making ``"vision"`` equivalent to ``"raycast"``.
        smoke_radius: Radius of a smoke cloud that blocks vision.
        smoke_height: How far above its landing point a smoke's blocking sphere
            is centred.
        fire_radius: Radius around a molotov within which the ground is denied.
        flash_threshold: A player counts as blinded (projects no vision) while
            more than this many seconds of flash blindness remain.
    """

    eye_height: float = 64.0
    crouch_eye_height: float = 46.0
    target_height: float = 46.0
    max_distance: float | None = None
    contest_margin: float = 200.0
    fov: float = 90.0
    smoke_radius: float = 144.0
    smoke_height: float = 60.0
    fire_radius: float = 150.0
    flash_threshold: float = 1.0

    def _core_kwargs(self) -> dict:
        """The subset passed straight to the Rust primitive."""
        return {
            "eye_height": self.eye_height,
            "crouch_eye_height": self.crouch_eye_height,
            "target_height": self.target_height,
            "max_distance": self.max_distance,
            "contest_margin": self.contest_margin,
            "fov": self.fov,
        }


@lru_cache(maxsize=8)
def _nav(map_name: str, version: int | None) -> NavMesh:
    return NavMesh(map_name, version=version)


@lru_cache(maxsize=8)
def _visibility(map_name: str, version: int | None) -> VisibilityChecker:
    return VisibilityChecker(map_name, version=version)


def _resolve_map(demo: Demo, map_name: str | None) -> str:
    if map_name is not None:
        return map_name
    name = demo.header.get("map_name")
    if not name:
        msg = "could not read map_name from the demo header; pass map_name=..."
        raise ValueError(msg)
    return name


def _players_at(group: pl.DataFrame, flash_threshold: float) -> list[tuple]:
    """``(x, y, z, side, crouched, blind, yaw)`` tuples for the living players in
    one tick's snapshot rows (dead players and non-playing sides are dropped).

    ``yaw`` is where the player is looking, which ``method="vision"`` needs for its
    field-of-view cone; it is ``None`` when the snapshot does not resolve it.
    """
    alive = group.filter(
        (pl.col("health") > 0)
        & pl.col("x").is_not_null()
        & pl.col("side").is_in(["terrorist", "counter-terrorist"])
    )
    return list(
        zip(
            alive["x"],
            alive["y"],
            alive["z"],
            alive["side"],
            alive["is_crouched"],
            alive["flash_duration"] > flash_threshold,
            alive["yaw"],
            strict=True,
        )
    )


def _active(events: pl.DataFrame, tick: int, radius: float, z_offset: float = 0.0) -> list[tuple]:
    """``(x, y, z, radius)`` spheres for the smoke/fire rows active at ``tick``."""
    if events.is_empty():
        return []
    live = events.filter((pl.col("start_tick") <= tick) & (pl.col("end_tick") >= tick))
    return [
        (x, y, z + z_offset, radius)
        for x, y, z in zip(live["x"], live["y"], live["z"], strict=True)
    ]


def _compute_at(
    tick: int,
    group: pl.DataFrame,
    *,
    method: Method,
    nav: NavMesh,
    vis: VisibilityChecker | None,
    smokes: pl.DataFrame,
    fires: pl.DataFrame,
    params: MapControlParams,
    detail: bool,
) -> dict:
    """Run one model for a single tick, gathering its players and occluders."""
    players = _players_at(group, params.flash_threshold)
    if method in LINE_OF_SIGHT_METHODS:
        # Smokes cut rays, so they apply to both line-of-sight models.
        occluders = _active(smokes, tick, params.smoke_radius, params.smoke_height)
        return compute_map_control(
            nav,
            players,
            visibility=vis,
            method=method,
            smokes=occluders,
            detail=detail,
            **params._core_kwargs(),
        )
    occluders = _active(fires, tick, params.fire_radius)
    return compute_map_control(
        nav,
        players,
        method="reachability",
        fires=occluders,
        detail=detail,
        **params._core_kwargs(),
    )


def map_control(
    demo: Demo,
    *,
    method: Method = "vision",
    ticks: int | list[int] | None = None,
    every: int | None = None,
    seconds: float | None = None,
    events: str | list[str] | None = None,
    start_tick: int | None = None,
    end_tick: int | None = None,
    params: MapControlParams | None = None,
    map_name: str | None = None,
    version: int | None = None,
) -> pl.DataFrame:
    """Map-control summary over time: one row of fractions per selected tick.

    Ticks are chosen exactly as in :meth:`awpy.Demo.snapshots` — pass any of
    ``ticks`` / ``every`` / ``seconds`` / ``events`` / ``start_tick`` /
    ``end_tick``. Since this samples the whole demo, prefer a coarse cadence
    (e.g. ``seconds=1``) or event ticks over every single tick.

    Args:
        demo: The parsed demo.
        method: ``"raycast"``, ``"vision"``, or ``"reachability"`` (see the
            module docs).
        ticks, every, seconds, events, start_tick, end_tick: Tick selection,
            forwarded to :meth:`awpy.Demo.snapshots`.
        params: Model parameters (defaults if omitted).
        map_name: Override the map (defaults to the demo header's map).
        version: awpy-data release for the nav/mesh assets (default: newest
            cached).

    Returns:
        A DataFrame with columns ``tick``, ``method``, ``ct``, ``t``,
        ``contested``, ``neutral``, ``net_control`` — the last five being the
        size-weighted fraction of the map in each bucket (``ct``/``t``/
        ``contested``/``neutral`` sum to 1), and ``net_control = ct - t``.
    """
    params = params or MapControlParams()
    name = _resolve_map(demo, map_name)
    nav = _nav(name, version)
    vis = _visibility(name, version) if method in LINE_OF_SIGHT_METHODS else None

    snaps = demo.snapshots(
        ticks=ticks,
        every=every,
        seconds=seconds,
        events=events,
        start_tick=start_tick,
        end_tick=end_tick,
    ).sort("tick")
    if method in LINE_OF_SIGHT_METHODS:
        demo.load("smokes")
        smokes, fires = demo.smokes, pl.DataFrame()
    else:
        demo.load("fires")
        smokes, fires = pl.DataFrame(), demo.fires

    rows: list[dict] = []
    for (tick,), group in snaps.group_by("tick", maintain_order=True):
        summary = _compute_at(
            int(tick),
            group,
            method=method,
            nav=nav,
            vis=vis,
            smokes=smokes,
            fires=fires,
            params=params,
            detail=False,
        )
        rows.append(
            {
                "tick": int(tick),
                "method": method,
                "ct": summary["ct_fraction"],
                "t": summary["t_fraction"],
                "contested": summary["contested_fraction"],
                "neutral": summary["neutral_fraction"],
                "net_control": summary["net_control"],
            }
        )

    schema = {
        "tick": pl.Int64,
        "method": pl.String,
        **{c: pl.Float64 for c in _SUMMARY_COLUMNS},
    }
    return pl.DataFrame(rows, schema=schema)


def map_control_at(
    demo: Demo,
    tick: int,
    *,
    method: Method = "vision",
    params: MapControlParams | None = None,
    map_name: str | None = None,
    version: int | None = None,
) -> pl.DataFrame:
    """Per-area map control at a single tick.

    Args:
        demo: The parsed demo.
        tick: The tick to evaluate.
        method: ``"raycast"``, ``"vision"``, or ``"reachability"`` (see the
            module docs).
        params: Model parameters (defaults if omitted).
        map_name: Override the map (defaults to the demo header's map).
        version: awpy-data release for the nav/mesh assets.

    Returns:
        One row per nav area, with ``area_id``, ``control`` (``"ct"`` / ``"t"``
        / ``"contested"`` / ``"neutral"``), ``ct`` / ``t`` (does that side hold
        it, alone or contested), and the area's ``centroid_x`` / ``centroid_y``
        / ``centroid_z`` / ``size`` (joined from the nav mesh) for plotting.
    """
    params = params or MapControlParams()
    name = _resolve_map(demo, map_name)
    nav = _nav(name, version)
    vis = _visibility(name, version) if method in LINE_OF_SIGHT_METHODS else None

    snap = demo.snapshots(ticks=tick)
    group = snap.filter(pl.col("tick") == tick) if "tick" in snap.columns else snap
    if method in LINE_OF_SIGHT_METHODS:
        demo.load("smokes")
        smokes, fires = demo.smokes, pl.DataFrame()
    else:
        demo.load("fires")
        smokes, fires = pl.DataFrame(), demo.fires
    detail = _compute_at(
        tick,
        group,
        method=method,
        nav=nav,
        vis=vis,
        smokes=smokes,
        fires=fires,
        params=params,
        detail=True,
    )
    areas = pl.DataFrame(
        {
            "area_id": detail["area_ids"],
            "control": detail["control"],
            "ct": detail["ct"],
            "t": detail["t"],
        }
    )
    geometry = nav.areas.select(["area_id", "centroid_x", "centroid_y", "centroid_z", "size"])
    return areas.join(geometry, on="area_id", how="left")
