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
from typing import TYPE_CHECKING, Any, Literal, TypedDict

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

#: Supported Awpy map-control methods.
Method = Literal["raycast", "vision", "reachability"]

#: Methods that cast rays through the collision mesh, and so need a
#: :class:`~awpy.VisibilityChecker`.
LINE_OF_SIGHT_METHODS: frozenset[str] = frozenset({"raycast", "vision"})

#: Summary columns of a :func:`map_control` time series (besides ``tick`` /
#: ``method``): the size-weighted fraction of the map in each bucket, and the
#: signed CT-minus-T difference.
_SUMMARY_COLUMNS = ("ct", "t", "contested", "neutral", "net_control")


class _CoreParams(TypedDict):
    """Typed keyword arguments for the native map-control calculation."""

    eye_height: float
    crouch_eye_height: float
    target_height: float
    max_distance: float | None
    contest_margin: float
    fov: float


@dataclass(frozen=True)
class MapControlParams:
    """Set Awpy map-control inputs in Hammer units and degrees.

    Attributes:
        eye_height: Standing ray origin above the feet; default 64 Hammer units.
        crouch_eye_height: Crouched ray origin above the feet; default 46 Hammer units.
        target_height: Ray endpoint above a navigation area; default 46 Hammer units.
        max_distance: Maximum ray distance, or ``None`` for no limit.
        contest_margin: Maximum travel-distance difference for a contested area; default 200.
        fov: Horizontal field of view for vision; default 90 degrees. Values of 360 or more remove
            the limit.
        smoke_radius: Smoke sphere radius; default 144 Hammer units.
        smoke_height: Smoke sphere center above its landing point; default 60 Hammer units.
        fire_radius: Blocked ground radius around a fire; default 150 Hammer units.
        flash_threshold: Recorded flash onset duration above which a currently blinded player
            contributes no sight; default 1 second.
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

    def _core_kwargs(self) -> _CoreParams:
        """Select parameters accepted by the native map-control function.

        Returns:
            Ray heights, range limit, contest margin, and field of view.
        """
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
    """Reuse a cached CS2 navigation mesh.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The loaded ``NavMesh``.
    """
    return NavMesh(map_name, version=version)


@lru_cache(maxsize=8)
def _visibility(map_name: str, version: int | None) -> VisibilityChecker:
    """Reuse a cached CS2 collision checker.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The loaded ``VisibilityChecker``.
    """
    return VisibilityChecker(map_name, version=version)


def _resolve_map(demo: Demo, map_name: str | None) -> str:
    """Select an explicit CS2 map or the demo header map.

    Args:
        demo: The source demo.
        map_name: Explicit map override, or ``None``.

    Returns:
        The selected map name.

    Raises:
        ValueError: If no map name is available.
    """
    if map_name is not None:
        return map_name
    name = demo.header.get("map_name")
    if not name:
        msg = "could not read map_name from the demo header; pass map_name=..."
        raise ValueError(msg)
    return name


def _players_at(
    group: pl.DataFrame, flash_threshold: float
) -> list[tuple[float, float, float, str, bool, bool, float | None]]:
    """Read living players for a map-control query.

    Args:
        group: Player snapshots at one tick.
        flash_threshold: Minimum onset flash duration to suppress sight.

    Returns:
        ``(x, y, z, side, crouched, blind, yaw)`` tuples. Missing yaw is ``None``.
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


def _active(
    events: pl.DataFrame, tick: int, radius: float, z_offset: float = 0.0
) -> list[tuple[float, float, float, float]]:
    """Read smoke or fire spheres active at one tick.

    Args:
        events: Smoke or fire interval rows.
        tick: Local demo tick.
        radius: Sphere radius in Hammer units.
        z_offset: Height to add to the recorded origin.

    Returns:
        ``(x, y, z, radius)`` tuples for inclusive active intervals.
    """
    if events.is_empty():
        return []
    live = events.filter((pl.col("start_tick") <= tick) & (pl.col("end_tick") >= tick))
    return [
        (x, y, z + z_offset, radius)
        for x, y, z in zip(live["x"], live["y"], live["z"], strict=True)
    ]


def _occluders(demo: Demo, method: Method) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Load the projectile inputs needed by one map-control model.

    Args:
        demo: The source demo.
        method: Map-control method.

    Returns:
        Smoke and fire DataFrames; the unused input is empty.
    """
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
) -> dict[str, Any]:
    """Calculate map control from the selected tick inputs.

    Args:
        tick: Local demo tick.
        group: Player snapshots at this tick.
        method: Map-control method.
        nav: The map navigation mesh.
        vis: Collision checker for sight models, or ``None``.
        smokes: Recorded smoke intervals.
        fires: Recorded fire intervals.
        params: Model settings.
        detail: Include per-area arrays as well as summary fractions.

    Returns:
        Native summary values and optional per-area arrays.
    """
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
    """Estimate CS2 map control as a Polars time series.

    Args:
        demo: The Awpy demo whose player state is queried.
        method: ``"raycast"`` for all-direction sight, ``"vision"`` for a horizontal field of view,
            or ``"reachability"`` for graph travel distance.
        ticks: One local demo tick or a list of local ticks.
        every: Positive sampling stride in ticks. Do not combine with ``seconds``.
        seconds: Positive sampling interval in seconds. Do not combine with ``every``.
        events: One game-event name or a list of names whose ticks are selected.
        start_tick: Inclusive lower bound for the tick selection.
        end_tick: Inclusive upper bound for the tick selection.
        part: Zero-based recording index. Required for multipart local ticks or windows.
        params: Model settings. Omit for ``MapControlParams`` defaults.
        map_name: Override the map name in the demo header.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        One row per selected tick with ``method``, ``ct``, ``t``, ``contested``, ``neutral``, and
        ``net_control``. The first four fractions are weighted by area size and sum to 1.
        ``net_control`` is CT minus T. Multipart queries also include ``part``.

    Raises:
        ValueError: If the method, tick selection, or map name is invalid.

    Notes:
        Sight models account for static geometry, active smokes, and eligible flash state.
        Reachability accounts for active fires. These are control estimates, not exact player
        perception.

    Examples:
        >>> from awpy import Demo
        >>> from awpy.map_control import map_control
        >>> result = map_control(Demo("match.dem"), seconds=1.0)
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

    rows: list[dict[str, Any]] = []
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
    """Estimate CS2 control for each navigation area at one tick.

    Args:
        demo: The Awpy demo whose player state is queried.
        tick: Local demo tick to evaluate.
        part: Zero-based recording index. Required for multipart local ticks or windows.
        method: ``"raycast"`` for all-direction sight, ``"vision"`` for a horizontal field of view,
            or ``"reachability"`` for graph travel distance.
        params: Model settings. Omit for ``MapControlParams`` defaults.
        map_name: Override the map name in the demo header.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        A Polars DataFrame with ``area_id``, ``control``, ``ct``, ``t``, ``centroid_x``,
        ``centroid_y``, ``centroid_z``, and ``size``. Labels are ``ct``, ``t``, ``contested``, or
        ``neutral``. Multipart queries also include ``part``.

    Raises:
        ValueError: If the method, tick selection, or map name is invalid.
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
