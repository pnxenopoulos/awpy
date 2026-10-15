"""Estimate map control from player snapshots.

Models:

- ``raycast``: line of sight in any direction.
- ``vision``: line of sight within the horizontal field of view.
- ``reachability``: shortest travel distance over the nav graph.

Smokes block rays. Blinded players do not contribute to line-of-sight models.
Fires block travel paths. Results estimate control, not exact player perception.

Use :func:`map_control` for a time series or :func:`map_control_at` for
per-area labels. Assets are supplied by :mod:`awpy.data`.
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
    """Map-control parameters. Distances use Hammer units.

    Attributes:
        eye_height: Standing eye height above the feet — where vision rays start.
        crouch_eye_height: Eye height when crouched.
        target_height: Ray endpoint height above each area's floor.
        max_distance: Optional cap on vision range; ``None`` is unbounded.
        contest_margin: Travel-distance tie band — areas whose two sides' travel
            distances differ by no more than this are contested.
        fov: Horizontal field of view in degrees for ``method="vision"`` — an area
            counts only within ``fov / 2`` either side of where the player looks.
            ``360`` or more removes the limit.
        smoke_radius: Radius of a smoke cloud that blocks vision.
        smoke_height: How far above its landing point a smoke's blocking sphere
            is centred.
        fire_radius: Radius around a molotov within which the ground is denied.
        flash_threshold: A currently flashing player projects no vision when
            the replicated flash duration is greater than this value. This
            filters out short partial flashes.
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
        """Parameters passed to the Rust computation."""
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
    """Return living players as ``(x, y, z, side, crouched, blind, yaw)`` tuples.

    Exclude non-playing sides. Unresolved yaw is ``None``.
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
            alive["is_blinded"] & (alive["flash_duration"] > flash_threshold),
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


def _occluders(demo: Demo, method: Method) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Load only the projectile dataset required by the model."""
    if method in LINE_OF_SIGHT_METHODS:
        demo.load("smokes")
        return demo.smokes, pl.DataFrame()
    demo.load("fires")
    return pl.DataFrame(), demo.fires


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
    part: int | None = None,
    params: MapControlParams | None = None,
    map_name: str | None = None,
    version: int | None = None,
) -> pl.DataFrame:
    """Map-control summary over time: one row of fractions per selected tick.

    Ticks are chosen exactly as in :meth:`awpy.Demo.snapshots` — pass any of
    ``ticks`` / ``every`` / ``seconds`` / ``events`` / ``start_tick`` /
    ``end_tick``. Use a coarse stride
    (for example, ``seconds=1``) or event ticks to reduce computation.

    Args:
        demo: The parsed demo.
        method: ``"raycast"``, ``"vision"``, or ``"reachability"`` (see the
            module docs).
        part: Source recording for a multipart local-tick query.
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
        **({"part": part} if part is not None else {}),
    )
    smokes, fires = _occluders(demo, method)

    rows: list[dict] = []
    keys = ["part", "tick"] if "part" in snaps.columns else ["tick"]
    for coordinate, group in snaps.sort(keys).group_by(keys, maintain_order=True):
        tick = coordinate[-1]
        source = coordinate[0] if len(coordinate) == 2 else None
        part_smokes = (
            smokes.filter(pl.col("part") == source) if "part" in smokes.columns else smokes
        )
        part_fires = fires.filter(pl.col("part") == source) if "part" in fires.columns else fires
        summary = _compute_at(
            int(tick),
            group,
            method=method,
            nav=nav,
            vis=vis,
            smokes=part_smokes,
            fires=part_fires,
            params=params,
            detail=False,
        )
        rows.append(
            {
                **({"part": int(source)} if source is not None else {}),
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
        **({"part": pl.UInt32} if "part" in snaps.columns else {}),
        "tick": pl.Int64,
        "method": pl.String,
        **{c: pl.Float64 for c in _SUMMARY_COLUMNS},
    }
    return pl.DataFrame(rows, schema=schema)


def map_control_at(
    demo: Demo,
    tick: int,
    *,
    part: int | None = None,
    method: Method = "vision",
    params: MapControlParams | None = None,
    map_name: str | None = None,
    version: int | None = None,
) -> pl.DataFrame:
    """Per-area map control at a single tick.

    Args:
        demo: The parsed demo.
        tick: The local tick to evaluate.
        part: Source recording when the demo has multiple parts.
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

    snap = demo.snapshots(ticks=tick, **({"part": part} if part is not None else {}))
    group = snap.filter(pl.col("tick") == tick) if "tick" in snap.columns else snap
    smokes, fires = _occluders(demo, method)
    if "part" in snap.columns:
        smokes = smokes.filter(pl.col("part") == part) if "part" in smokes.columns else smokes
        fires = fires.filter(pl.col("part") == part) if "part" in fires.columns else fires
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
    result = areas.join(geometry, on="area_id", how="left")
    return (
        result.with_columns(pl.lit(part, dtype=pl.UInt32).alias("part"))
        if "part" in snap.columns
        else result
    )
