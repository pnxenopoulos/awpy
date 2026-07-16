"""Plot CS2 demo data on radar images.

Everything draws onto a map's **radar image** — the 1024x1024 PNGs shipped by
``awpy-data`` and fetched on demand by :mod:`awpy.data`. Like the rest of awpy,
pass a map name and optionally pin an ``awpy-data`` release with ``version=``
(an integer ClientVersion); by default the newest cached release is used.

Requires matplotlib — install with ``pip install 'awpy[plot]'``.

Draw a game-state frame (players and the bomb at one moment)::

    from awpy import plot

    players = [
        plot.Player(x=-158.6, y=819.1, z=103.7, side="ct", hp=87, label="ct1"),
        plot.Player(x=1258.0, y=455.5, z=181.2, side="t", yaw=135.0),
    ]
    fig, ax = plot.frame("de_inferno", players, bomb=(200.0, 480.0, 90.0))
    fig.savefig("frame.png")

Heatmap of demo positions (any ``(x, y, z)`` rows — e.g. death locations)::

    from awpy import Demo, plot

    kills = Demo("match.dem").kills
    deaths = kills.select(["victim_x", "victim_y", "victim_z"]).rows()
    fig, ax = plot.heatmap("de_inferno", deaths, method="kde")

The building blocks are exposed too: :func:`radar` draws the bare map (pass its
``ax`` to other calls to layer plots), and :func:`world_to_pixel` /
:func:`pixel_to_world` convert between world and radar-pixel coordinates.
Multi-level maps (Nuke, Vertigo, Train, Baggage) have a second radar for the
lower level: pass ``lower=True`` to draw it; points are matched to the level
they're on via the map's altitude bands (:func:`is_lower_level`). To show a
game state spanning both levels, :func:`frame_levels` / :func:`heatmap_levels`
render one panel per level::

    fig, (upper, lower) = plot.frame_levels("de_nuke", players, bomb=bomb)
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

import polars as pl

try:
    import matplotlib.image as mpimg
    import matplotlib.patheffects as patheffects
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle, Patch, Polygon, Rectangle
    from matplotlib.transforms import Affine2D, ScaledTranslation
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    _msg = (
        "awpy.plot requires matplotlib -- install it with: "
        "uv add 'awpy[plot]' / pip install 'awpy[plot]'"
    )
    raise ImportError(_msg) from exc

from awpy import data
from awpy.map_control import MapControlParams, map_control_at

if TYPE_CHECKING:
    from awpy import Demo

__all__ = [
    "CONTESTED_COLOR",
    "CT_COLOR",
    "FIRE_RADIUS",
    "NEUTRAL_COLOR",
    "RADAR_SIZE",
    "SMOKE_RADIUS",
    "T_COLOR",
    "Player",
    "frame",
    "frame_levels",
    "gif",
    "has_lower_level",
    "heatmap",
    "heatmap_levels",
    "is_lower_level",
    "map_control",
    "pixel_to_world",
    "radar",
    "world_to_pixel",
]

#: Side length, in pixels, of the awpy-data radar images.
RADAR_SIZE = 1024

#: Default marker colors, keyed off :attr:`Player.side`.
T_COLOR = "#EAB308"
CT_COLOR = "#3B82F6"
NEUTRAL_COLOR = "#EF4444"

#: Fill color for map-control areas held by both sides at once (see
#: :func:`map_control`).
CONTESTED_COLOR = "#A855F7"

_BOMB_COLOR = "#F97316"

#: Marker-border color for the bomb carrier (red) and a planted bomb (green).
_BOMB_CARRIER_BORDER = "#EF4444"
_BOMB_PLANTED_BORDER = "#22C55E"
#: Border width, in points, of a highlighted (carrier / planted) marker.
_HIGHLIGHT_BORDER_WIDTH = 1.8

#: On-screen radius, in points, of the ``s=72`` player marker (measured). The
#: yaw tick extends this far so it reaches the marker edge at any zoom.
_MARKER_RADIUS_PT = 3.7

#: HP/armor bar geometry in screen points (see :func:`_marker_offset`). The bars
#: are anchored to the marker in points, not data units, so they stay the same
#: size relative to the marker at any zoom. Values reproduce the 1x look.
_BAR_WIDTH_PT = 9.6
_BAR_HEIGHT_PT = 1.92
_BAR_GAP_PT = 0.48
_BAR_TOP_PT = 3.84  # top of the first bar, below the marker center
#: Label baseline offset above the marker center, in screen points.
_LABEL_OFFSET_PT = 4.0

#: Smoke-cloud fill and burning-inferno fill.
_SMOKE_COLOR = "#D1D5DB"
_FIRE_COLOR = "#F97316"

#: World-unit radii of a deployed smoke cloud and a molotov/incendiary fire.
SMOKE_RADIUS = 144.0
FIRE_RADIUS = 150.0

#: Trajectory-line color per grenade ``type`` (as spelled by ``Demo.grenades``).
_GRENADE_COLORS = {
    "smoke": _SMOKE_COLOR,
    "smokegrenade": _SMOKE_COLOR,
    "molotov": _FIRE_COLOR,
    "incendiary": _FIRE_COLOR,
    "inferno": _FIRE_COLOR,
    "he": "#EF4444",
    "hegrenade": "#EF4444",
    "flashbang": "#FACC15",
    "decoy": "#22C55E",
}
_GRENADE_DEFAULT_COLOR = "#E5E7EB"

Point2 = tuple[float, float]
Point3 = tuple[float, float, float]


# --- coordinates ---------------------------------------------------------------


def _meta(map_name: str, version: int | None) -> dict:
    """The map's entry in ``map_data.json`` (world->radar transform + levels)."""
    map_data = data.map_data(version)
    try:
        return map_data[map_name]
    except KeyError:
        tag = data.resolve_version(version)
        raise KeyError(f"no map data for '{map_name}' in {data.DATA_REPO} {tag}") from None


def world_to_pixel(map_name: str, point: Sequence[float], *, version: int | None = None) -> Point2:
    """Convert a world ``(x, y, ...)`` position to radar-pixel ``(px, py)``.

    Pixel coordinates have the origin at the radar's top-left corner, with
    ``py`` growing downward (matplotlib image convention).
    """
    meta = _meta(map_name, version)
    scale = meta["scale"]
    return (point[0] - meta["pos_x"]) / scale, (meta["pos_y"] - point[1]) / scale


def pixel_to_world(map_name: str, point: Sequence[float], *, version: int | None = None) -> Point2:
    """Convert a radar-pixel ``(px, py)`` back to a world ``(x, y)`` position."""
    meta = _meta(map_name, version)
    scale = meta["scale"]
    return point[0] * scale + meta["pos_x"], meta["pos_y"] - point[1] * scale


def is_lower_level(map_name: str, z: float, *, version: int | None = None) -> bool:
    """Is altitude ``z`` in the map's ``lower`` vertical section?

    Multi-level maps (Nuke, Vertigo, Train, Baggage) publish altitude bands in
    ``map_data.json``; single-level maps have none, so this returns ``False``.
    """
    sections = _meta(map_name, version).get("verticalsections") or {}
    lower = sections.get("lower")
    if lower is None:
        return False
    return float(lower["AltitudeMin"]) <= z < float(lower["AltitudeMax"])


def has_lower_level(map_name: str, *, version: int | None = None) -> bool:
    """Does the map have a lower vertical level (and a ``_lower`` radar)?"""
    sections = _meta(map_name, version).get("verticalsections") or {}
    return "lower" in sections


def _split_by_level(
    map_name: str,
    points: Iterable[Sequence[float]],
    *,
    lower: bool,
    version: int | None,
) -> tuple[list[float], list[float], int]:
    """Project points to on-radar pixels; return (xs, ys, n_dropped_off_level).

    A point is on-level when its z altitude matches the radar being drawn
    (points without a z count as upper-level). Off-radar points are dropped
    silently; off-level points are counted so callers can warn.
    """
    xs: list[float] = []
    ys: list[float] = []
    off_level = 0
    for point in points:
        z = point[2] if len(point) > 2 else 0.0
        if is_lower_level(map_name, z, version=version) != lower:
            off_level += 1
            continue
        px, py = world_to_pixel(map_name, point, version=version)
        if 0 <= px <= RADAR_SIZE and 0 <= py <= RADAR_SIZE:
            xs.append(px)
            ys.append(py)
    return xs, ys, off_level


# --- radar canvas ----------------------------------------------------------------


def radar(
    map_name: str,
    *,
    version: int | None = None,
    lower: bool = False,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Draw a map's radar image — the canvas every other function draws onto.

    Args:
        map_name: Map to draw, e.g. ``"de_inferno"``.
        version: awpy-data release to use (default: newest cached).
        lower: Draw the lower-level radar of a multi-level map.
        ax: Draw onto an existing axes instead of creating a new figure.

    Returns:
        The matplotlib ``(Figure, Axes)``, axis off, one radar pixel per
        data unit.
    """
    image = mpimg.imread(data.radar_path(map_name, version, lower=lower))
    if ax is None:
        fig, ax = plt.subplots(figsize=(RADAR_SIZE / 300, RADAR_SIZE / 300), dpi=300)
        fig.patch.set_facecolor("black")
        fig.tight_layout(pad=0.05)
    else:
        fig = ax.get_figure(root=True)
        if fig is None:  # pragma: no cover - an Axes detached from any figure
            raise ValueError("ax is not attached to a figure")
    ax.imshow(image, zorder=0)
    ax.set_xlim(0, image.shape[1])
    ax.set_ylim(image.shape[0], 0)
    ax.axis("off")
    return fig, ax


# --- game state ------------------------------------------------------------------


@dataclass
class Player:
    """Render state for one player in a :func:`frame`.

    Only ``x``/``y`` are required. ``side`` picks the marker color (``"t"`` /
    ``"ct"``, or the demo dataframes' ``"terrorist"`` / ``"counter-terrorist"``,
    any case); ``hp=0`` draws the player as dead (a dim cross);
    ``yaw`` (degrees, 0 = +x, counter-clockwise) draws a view-direction tick;
    ``hp``/``armor`` draw bars under the marker; ``label`` prints below;
    ``has_bomb`` gives the marker a red border (the player carrying the bomb).
    """

    x: float
    y: float
    z: float = 0.0
    side: str | None = None
    hp: int | None = None
    armor: int | None = None
    yaw: float | None = None
    label: str | None = None
    color: str | None = None
    has_bomb: bool = False

    @property
    def _color(self) -> str:
        if self.color is not None:
            return self.color
        # Demo dataframes say "terrorist"/"counter-terrorist"; people say "t"/"ct".
        side = (self.side or "").lower()
        if side in ("ct", "counter-terrorist"):
            return CT_COLOR
        if side in ("t", "terrorist"):
            return T_COLOR
        return NEUTRAL_COLOR


def _marker_offset(ax: Axes, px: float, py: float):
    """A transform whose coordinates are *screen points* offset from the data
    point ``(px, py)``: ``+x`` right, ``+y`` down. Anchored at the marker so
    attachments (HP/armor bars, label) track it, but sized in points so they
    don't grow when the axes is zoomed — the same trick the yaw tick uses.

    The anchor is snapped to whole data units so every player's bars share one
    sub-pixel grid and rasterize to identical heights (a fractional anchor makes
    a bar's height wobble by a pixel with the player's sub-pixel position).
    """
    fig = ax.get_figure(root=True)
    if fig is None:  # pragma: no cover - an Axes detached from any figure
        raise ValueError("ax is not attached to a figure")
    per_point = fig.dpi / 72.0  # points -> display pixels
    # Scale points to pixels, flipping y so +y is downward on screen, then pin
    # the origin to the marker's (pixel-snapped) data position. `transData` is a
    # general Transform in the stubs but ScaledTranslation accepts it at runtime.
    return Affine2D().scale(per_point, -per_point) + ScaledTranslation(
        round(px),
        round(py),
        ax.transData,  # ty: ignore[invalid-argument-type]
    )


def _draw_player(ax: Axes, px: float, py: float, player: Player, alpha: float) -> None:
    color = player._color
    if player.hp == 0:
        ax.scatter(
            px, py, s=48, marker="x", color=color, linewidths=1.5, alpha=alpha * 0.5, zorder=10
        )
        return

    # The bomb carrier's marker gets a red border (in place of the usual black),
    # hugging the circle exactly since it's the marker's own edge.
    edge = _BOMB_CARRIER_BORDER if player.has_bomb else "black"
    edge_width = _HIGHLIGHT_BORDER_WIDTH if player.has_bomb else 0.8
    ax.scatter(
        px, py, s=72, color=color, edgecolors=edge, linewidths=edge_width, alpha=alpha, zorder=11
    )

    if player.yaw is not None:
        # A view-direction tick from the marker center to its edge. Drawn as a
        # points offset (like the marker itself, which is sized in points) so it
        # stays inside the circle at any zoom — a data-unit line would grow past
        # the fixed-size marker when zoomed in. World +y (yaw 90°) points up on
        # the radar, i.e. toward smaller py.
        dx = math.cos(math.radians(player.yaw))
        dy = -math.sin(math.radians(player.yaw))
        tick = ax.annotate(
            "",
            xy=(px, py),
            xycoords="data",
            xytext=(dx * _MARKER_RADIUS_PT, dy * _MARKER_RADIUS_PT),
            textcoords="offset points",
            arrowprops={
                "arrowstyle": "-",
                "color": "white",
                "linewidth": 1.2,
                "shrinkA": 0,
                "shrinkB": 1.5,
                "capstyle": "round",
                "alpha": alpha,
            },
            zorder=12,
        )
        if tick.arrow_patch is not None:
            tick.arrow_patch.set_path_effects(
                [patheffects.withStroke(linewidth=2.2, foreground="black")]
            )

    # HP/armor bars, anchored to the marker in screen points (see
    # _marker_offset) so they keep their size relative to the fixed-size marker
    # at any zoom, centered beneath it. Point y grows downward here.
    trans = _marker_offset(ax, px, py)
    bar_left = -_BAR_WIDTH_PT / 2
    # (value, filled color, depleted color): health fills green and drains to
    # red; armor fills light grey and drains to dark grey.
    bars = (
        (player.hp, "#22C55E", "#B91C1C"),
        (player.armor, "#D1D5DB", "#4B5563"),
    )
    for row, (value, filled, depleted) in enumerate(bars):
        if value is None:
            continue
        y0 = _BAR_TOP_PT + row * (_BAR_HEIGHT_PT + _BAR_GAP_PT)
        # Depleted track spans the full width; the filled portion sits on top,
        # so whatever is missing shows through in the depleted color.
        ax.add_patch(
            Rectangle(
                (bar_left, y0),
                _BAR_WIDTH_PT,
                _BAR_HEIGHT_PT,
                facecolor=depleted,
                alpha=alpha,
                zorder=12,
                transform=trans,
            )
        )
        frac = max(0, min(value, 100)) / 100
        if frac > 0:
            ax.add_patch(
                Rectangle(
                    (bar_left, y0),
                    _BAR_WIDTH_PT * frac,
                    _BAR_HEIGHT_PT,
                    facecolor=filled,
                    alpha=alpha,
                    zorder=13,
                    transform=trans,
                )
            )
        # Black frame on top, so each bar reads as a distinct pill.
        ax.add_patch(
            Rectangle(
                (bar_left, y0),
                _BAR_WIDTH_PT,
                _BAR_HEIGHT_PT,
                facecolor="none",
                edgecolor="black",
                linewidth=0.8,
                alpha=alpha,
                zorder=14,
                transform=trans,
            )
        )

    if player.label:
        # Anchored above the marker by a point offset, so it too stays put on zoom.
        ax.annotate(
            player.label,
            (px, py),
            textcoords="offset points",
            xytext=(0, _LABEL_OFFSET_PT),
            ha="center",
            va="bottom",
            color="white",
            fontsize=5,
            alpha=alpha,
            zorder=14,
            path_effects=[patheffects.withStroke(linewidth=1.5, foreground="black")],
        )


def _pixel_radius(map_name: str, world_radius: float, *, version: int | None) -> float:
    """A world-unit radius in radar pixels (the transform's scale is uniform)."""
    return world_radius / _meta(map_name, version)["scale"]


def _draw_area(
    ax: Axes, px: float, py: float, radius: float, color: str, alpha: float, zorder: int
) -> None:
    """A soft translucent disc (a smoke cloud or a burning inferno)."""
    ax.add_patch(
        Circle(
            (px, py),
            radius,
            facecolor=color,
            edgecolor=color,
            linewidth=0.8,
            alpha=alpha,
            zorder=zorder,
        )
    )


def _draw_grenade(ax: Axes, px: float, py: float, color: str, alpha: float) -> None:
    """A live grenade projectile: a small circle at its current position."""
    ax.scatter(
        px,
        py,
        s=28,
        color=color,
        edgecolors="black",
        linewidths=0.8,
        alpha=alpha,
        zorder=8,
    )


def _grenade_marker(
    entry: Sequence[float] | Mapping[str, Any],
) -> tuple[Sequence[float], str] | None:
    """Resolve one grenade entry to its ``(position, color)``, or ``None`` to skip.

    An entry is either a world ``(x, y[, z])`` position, or a mapping carrying
    the position (``pos``, or ``x``/``y``/``z`` keys — the shape of a
    ``Demo.grenades`` row) and an optional ``type``/``color``.
    """
    if not isinstance(entry, Mapping):
        return entry, _GRENADE_DEFAULT_COLOR
    raw = entry.get("pos")
    if raw is None and "x" in entry:
        raw = (entry.get("x"), entry.get("y"), entry.get("z", 0.0))
    if raw is None:
        return None
    color = entry.get("color") or _GRENADE_COLORS.get(
        str(entry.get("type") or "").lower(), _GRENADE_DEFAULT_COLOR
    )
    return cast("Sequence[float]", raw), str(color)


def frame(
    map_name: str,
    players: Iterable[Player],
    *,
    bomb: Sequence[float] | None = None,
    bomb_planted: bool = False,
    smokes: Iterable[Sequence[float]] | None = None,
    fires: Iterable[Sequence[float]] | None = None,
    grenades: Iterable[Sequence[float] | Mapping[str, Any]] | None = None,
    smoke_radius: float = SMOKE_RADIUS,
    fire_radius: float = FIRE_RADIUS,
    version: int | None = None,
    lower: bool = False,
    off_level_alpha: float = 0.3,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Plot one game-state frame: players, bomb, smokes, fires and grenade paths.

    Args:
        map_name: Map to draw, e.g. ``"de_inferno"``.
        players: A :class:`Player` per player to draw. Set ``has_bomb`` on the
            carrier to give its marker a red border.
        bomb: World ``(x, y, z)`` of the bomb, drawn as an orange diamond.
        bomb_planted: Give the bomb a green border to mark it planted and ticking.
        smokes: World ``(x, y[, z])`` centers of active smoke clouds, each drawn
            as a translucent grey disc of ``smoke_radius`` world units.
        fires: World ``(x, y[, z])`` origins of burning infernos (molotov /
            incendiary), each drawn as a translucent orange disc of
            ``fire_radius`` world units.
        grenades: Live grenade projectiles, each drawn as a small circle at its
            current position. An entry is either a world ``(x, y[, z])``
            position, or a dict carrying the position (``pos``, or ``x``/``y``/
            ``z`` keys — a ``Demo.grenades`` row) plus an optional ``type``
            (e.g. ``"smoke"``, ``"molotov"``, ``"he"``) that colors it, or an
            explicit ``color``. Pass only in-flight grenades (filter the row to
            the frame's tick): a projectile's rows end when it detonates, so the
            grenade naturally disappears as its smoke or inferno appears.
        smoke_radius: Smoke-cloud radius in world units (default ~144).
        fire_radius: Inferno radius in world units (default ~150).
        version: awpy-data release to use (default: newest cached).
        lower: Draw the lower-level radar of a multi-level map.
        off_level_alpha: Opacity for markers whose altitude is on the *other*
            level of a multi-level map; ``0`` hides them entirely.
        ax: Draw onto an existing axes instead of creating a new figure.

    Returns:
        The matplotlib ``(Figure, Axes)``.
    """
    fig, ax = radar(map_name, version=version, lower=lower, ax=ax)

    def _level_alpha(z: float) -> float:
        return 1.0 if is_lower_level(map_name, z, version=version) == lower else off_level_alpha

    def _in_bounds(px: float, py: float) -> bool:
        return 0 <= px <= RADAR_SIZE and 0 <= py <= RADAR_SIZE

    # Area effects sit under the players; fires under smokes (smoke smothers fire).
    for source, color, world_r, zorder, base_alpha in (
        (fires, _FIRE_COLOR, fire_radius, 2, 0.45),
        (smokes, _SMOKE_COLOR, smoke_radius, 3, 0.55),
    ):
        if source is None:
            continue
        radius = _pixel_radius(map_name, world_r, version=version)
        for pos in source:
            alpha = _level_alpha(pos[2] if len(pos) > 2 else 0.0)
            if alpha <= 0:
                continue
            px, py = world_to_pixel(map_name, pos, version=version)
            if _in_bounds(px, py):
                _draw_area(ax, px, py, radius, color, base_alpha * alpha, zorder)

    if grenades is not None:
        for entry in grenades:
            spec = _grenade_marker(entry)
            if spec is None:
                continue
            pos, color = spec
            alpha = _level_alpha(pos[2] if len(pos) > 2 else 0.0)
            if alpha <= 0:
                continue
            px, py = world_to_pixel(map_name, pos, version=version)
            if _in_bounds(px, py):
                _draw_grenade(ax, px, py, color, alpha)

    for player in players:
        alpha = _level_alpha(player.z)
        if alpha <= 0:
            continue
        px, py = world_to_pixel(map_name, (player.x, player.y), version=version)
        if _in_bounds(px, py):
            _draw_player(ax, px, py, player, alpha)

    if bomb is not None:
        alpha = _level_alpha(bomb[2] if len(bomb) > 2 else 0.0)
        if alpha > 0:
            px, py = world_to_pixel(map_name, bomb, version=version)
            # A planted bomb gets a green border on its diamond (in place of the
            # usual black), hugging the diamond since it's the marker's own edge.
            edge = _BOMB_PLANTED_BORDER if bomb_planted else "black"
            edge_width = _HIGHLIGHT_BORDER_WIDTH if bomb_planted else 0.8
            ax.scatter(
                px,
                py,
                s=40,
                marker="D",
                color=_BOMB_COLOR,
                edgecolors=edge,
                linewidths=edge_width,
                alpha=alpha,
                zorder=15,
            )

    return fig, ax


def _level_panels(map_name: str, *, version: int | None) -> tuple[Figure, tuple[Axes, ...]]:
    """A figure with one radar-sized panel per vertical level (upper first)."""
    n_panels = 2 if has_lower_level(map_name, version=version) else 1
    fig, axes_grid = plt.subplots(
        1,
        n_panels,
        figsize=(n_panels * RADAR_SIZE / 300, RADAR_SIZE / 300),
        dpi=300,
        squeeze=False,
    )
    axes = tuple(axes_grid[0])
    fig.patch.set_facecolor("black")
    if n_panels == 2:
        for panel, label in zip(axes, ("upper", "lower"), strict=True):
            panel.text(
                0.02,
                0.98,
                label,
                transform=panel.transAxes,
                ha="left",
                va="top",
                color="white",
                fontsize=7,
                zorder=20,
                path_effects=[patheffects.withStroke(linewidth=1.5, foreground="black")],
            )
    return fig, axes


def frame_levels(
    map_name: str,
    players: Iterable[Player],
    *,
    bomb: Sequence[float] | None = None,
    bomb_planted: bool = False,
    version: int | None = None,
) -> tuple[Figure, tuple[Axes, ...]]:
    """Plot a game-state frame with one radar panel per vertical level.

    On a multi-level map (Nuke, Vertigo, Train, Baggage) this returns two
    panels — upper and lower — with every player and the bomb drawn at full
    opacity on the panel matching their altitude. On a single-level map it
    degrades to one panel, so callers never need to special-case the map.

    Args:
        map_name: Map to draw, e.g. ``"de_nuke"``.
        players: A :class:`Player` per player to draw. Set ``has_bomb`` on the
            carrier to give its marker a red border.
        bomb: World ``(x, y, z)`` of the bomb, drawn as an orange diamond.
        bomb_planted: Give the bomb a green border to mark it planted and ticking.
        version: awpy-data release to use (default: newest cached).

    Returns:
        The matplotlib ``(Figure, (Axes, ...))`` — ``(upper, lower)`` panels,
        or a 1-tuple for single-level maps.
    """
    players = list(players)  # drawn once per panel
    fig, axes = _level_panels(map_name, version=version)
    for panel, lower in zip(axes, (False, True), strict=False):  # 1 panel on flat maps
        frame(
            map_name,
            players,
            bomb=bomb,
            bomb_planted=bomb_planted,
            version=version,
            lower=lower,
            off_level_alpha=0.0,
            ax=panel,
        )
    fig.tight_layout(pad=0.05)
    return fig, axes


# --- map control -----------------------------------------------------------------

#: Fill color per map-control label; ``"neutral"`` is left unfilled so the bare
#: radar shows through.
_CONTROL_COLORS = {"ct": CT_COLOR, "t": T_COLOR, "contested": CONTESTED_COLOR}


def map_control(
    demo: Demo,
    tick: int,
    *,
    method: Literal["vision", "reachability"] = "vision",
    params: MapControlParams | None = None,
    players: bool = True,
    occluders: bool = True,
    legend: bool = True,
    alpha: float = 0.5,
    version: int | None = None,
    map_name: str | None = None,
    lower: bool = False,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Shade the map by which side controls each area at one tick.

    Computes :func:`awpy.map_control.map_control_at` for the tick and fills every
    nav area with its controlling side's color — blue (CT), yellow (T), purple
    (contested) — leaving neutral areas unshaded. The players are overlaid, along
    with the occluders that shaped the picture (smokes for ``"vision"``, molotovs
    for ``"reachability"``).

    Args:
        demo: The parsed demo.
        tick: The tick to draw.
        method: ``"vision"`` or ``"reachability"`` (see :mod:`awpy.map_control`).
        params: Model parameters (defaults if omitted).
        players: Overlay the players at the tick.
        occluders: Draw the active smokes (vision) or fires (reachability).
        legend: Draw a legend with each side's share of the map.
        alpha: Opacity of the area shading.
        version: awpy-data release to use (default: newest cached).
        map_name: Override the map (defaults to the demo header's map).
        lower: Draw the lower-level radar of a multi-level map.
        ax: Draw onto an existing axes instead of creating a new figure.

    Returns:
        The matplotlib ``(Figure, Axes)``.
    """
    from awpy import NavMesh

    params = params or MapControlParams()
    if map_name is None:
        map_name = demo.header.get("map_name")
        if not map_name:
            msg = "could not read map_name from the demo header; pass map_name=..."
            raise ValueError(msg)

    control = map_control_at(
        demo, tick, method=method, params=params, map_name=map_name, version=version
    )
    labels = dict(zip(control["area_id"], control["control"], strict=True))
    nav = NavMesh(map_name, version=version)

    fig, ax = radar(map_name, version=version, lower=lower, ax=ax)

    # Fill each non-neutral area with its controlling side's color. Areas are
    # convex polygons; project their corners to radar pixels and drop a patch.
    for area_id, label in labels.items():
        color = _CONTROL_COLORS.get(label)
        if color is None:
            continue
        info = nav.area(int(area_id))
        if info is None or is_lower_level(map_name, info["centroid"][2], version=version) != lower:
            continue
        corners = [
            world_to_pixel(map_name, (cx, cy), version=version) for cx, cy, _ in info["corners"]
        ]
        ax.add_patch(
            Polygon(corners, closed=True, facecolor=color, edgecolor="none", alpha=alpha, zorder=4)
        )

    if occluders:
        source = demo.smokes if method == "vision" else demo.fires
        color = _SMOKE_COLOR if method == "vision" else _FIRE_COLOR
        world_r = params.smoke_radius if method == "vision" else params.fire_radius
        radius_px = _pixel_radius(map_name, world_r, version=version)
        active = source.filter((pl.col("start_tick") <= tick) & (pl.col("end_tick") >= tick))
        for x, y, z in zip(active["x"], active["y"], active["z"], strict=True):
            if is_lower_level(map_name, z, version=version) != lower:
                continue
            px, py = world_to_pixel(map_name, (x, y), version=version)
            if 0 <= px <= RADAR_SIZE and 0 <= py <= RADAR_SIZE:
                _draw_area(ax, px, py, radius_px, color, 0.5, zorder=6)

    if players:
        for row in demo.snapshots(ticks=tick).iter_rows(named=True):
            if row["x"] is None:
                continue
            z = row["z"] or 0.0
            if is_lower_level(map_name, z, version=version) != lower:
                continue
            px, py = world_to_pixel(map_name, (row["x"], row["y"]), version=version)
            if 0 <= px <= RADAR_SIZE and 0 <= py <= RADAR_SIZE:
                player = Player(
                    x=row["x"], y=row["y"], z=z, side=row["side"], hp=row["health"], yaw=row["yaw"]
                )
                _draw_player(ax, px, py, player, 1.0)

    if legend:
        _map_control_legend(ax, control)
    return fig, ax


def _map_control_legend(ax: Axes, control: pl.DataFrame) -> None:
    """A legend keying each control color to its size-weighted share of the map."""
    total = float(control["size"].sum()) or 1.0
    share = {
        row["control"]: row["size"] / total
        for row in control.group_by("control").agg(pl.col("size").sum()).iter_rows(named=True)
    }
    entries = [
        ("ct", "CT", CT_COLOR),
        ("t", "T", T_COLOR),
        ("contested", "Contested", CONTESTED_COLOR),
    ]
    handles = [
        Patch(facecolor=color, edgecolor="none", label=f"{name}  {100 * share.get(key, 0.0):.0f}%")
        for key, name, color in entries
    ]
    legend = ax.legend(
        handles=handles,
        loc="upper right",
        fontsize=5,
        framealpha=0.6,
        facecolor="black",
        edgecolor="none",
        labelcolor="white",
        handlelength=1.0,
        borderpad=0.5,
    )
    legend.set_zorder(20)


# --- heatmaps --------------------------------------------------------------------


def _gaussian_blur(grid: np.ndarray, sigma: float) -> np.ndarray:
    """Separable gaussian blur (so 'kde' heatmaps need no scipy)."""
    radius = max(1, int(3 * sigma))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-(offsets**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    blurred = np.apply_along_axis(np.convolve, 0, grid, kernel, mode="same")
    return np.apply_along_axis(np.convolve, 1, blurred, kernel, mode="same")


def heatmap(
    map_name: str,
    points: Iterable[Sequence[float]],
    *,
    method: Literal["hex", "hist", "kde"] = "hex",
    bins: int = 48,
    cmap: str = "magma",
    alpha: float = 0.8,
    bandwidth: float = 16.0,
    version: int | None = None,
    lower: bool = False,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Plot a density heatmap of world positions over the radar.

    Args:
        map_name: Map to draw, e.g. ``"de_inferno"``.
        points: World positions — ``(x, y)`` or ``(x, y, z)`` rows, e.g.
            ``kills.select(["victim_x", "victim_y", "victim_z"]).rows()``.
        method: ``"hex"`` (hexagonal binning), ``"hist"`` (square binning),
            or ``"kde"`` (gaussian-smoothed density).
        bins: Grid resolution — hexagons across the radar for ``hex``, cells
            per side for ``hist``. (``kde`` evaluates on a fixed fine grid.)
        cmap: Matplotlib colormap name.
        alpha: Overlay opacity.
        bandwidth: ``kde`` smoothing radius, in radar pixels.
        version: awpy-data release to use (default: newest cached).
        lower: Draw the lower-level radar; only points at lower-level
            altitudes are included (and vice versa for the upper radar —
            off-level points are skipped with a warning).
        ax: Draw onto an existing axes instead of creating a new figure.

    Returns:
        The matplotlib ``(Figure, Axes)``.

    Raises:
        ValueError: On an unknown ``method``.
    """
    if method not in ("hex", "hist", "kde"):
        raise ValueError(f"method must be 'hex', 'hist', or 'kde', not {method!r}")

    fig, ax = radar(map_name, version=version, lower=lower, ax=ax)
    xs, ys, off_level = _split_by_level(map_name, points, lower=lower, version=version)
    if off_level:
        warnings.warn(
            f"skipped {off_level} point(s) on the {'upper' if lower else 'lower'} level; "
            f"plot them with lower={not lower}",
            UserWarning,
            stacklevel=2,
        )
    if not xs:
        return fig, ax

    if method == "hex":
        ax.hexbin(
            xs,
            ys,
            gridsize=bins,
            extent=(0, RADAR_SIZE, 0, RADAR_SIZE),
            cmap=cmap,
            alpha=alpha,
            mincnt=1,
            linewidths=0.2,
            zorder=5,
        )
        return fig, ax

    grid_bins = bins if method == "hist" else 256
    grid, xedges, yedges = np.histogram2d(
        xs, ys, bins=grid_bins, range=[[0, RADAR_SIZE], [0, RADAR_SIZE]]
    )
    grid = grid.T  # histogram2d returns (x, y); pcolormesh wants (row=y, col=x)
    if method == "kde":
        grid = _gaussian_blur(grid, sigma=bandwidth * grid_bins / RADAR_SIZE)
        grid[grid < 0.01 * grid.max()] = 0.0
    masked = np.ma.masked_equal(grid, 0.0)
    ax.pcolormesh(xedges, yedges, masked, cmap=cmap, alpha=alpha, zorder=5)
    return fig, ax


def heatmap_levels(
    map_name: str,
    points: Iterable[Sequence[float]],
    *,
    method: Literal["hex", "hist", "kde"] = "hex",
    bins: int = 48,
    cmap: str = "magma",
    alpha: float = 0.8,
    bandwidth: float = 16.0,
    version: int | None = None,
) -> tuple[Figure, tuple[Axes, ...]]:
    """Plot a density heatmap with one radar panel per vertical level.

    The multi-panel counterpart of :func:`heatmap`: on a multi-level map every
    point lands on the panel matching its altitude (no points are skipped); on
    a single-level map it degrades to one panel. Arguments are those of
    :func:`heatmap`.

    Returns:
        The matplotlib ``(Figure, (Axes, ...))`` — ``(upper, lower)`` panels,
        or a 1-tuple for single-level maps.
    """
    points = [tuple(point) for point in points]  # split once per panel
    fig, axes = _level_panels(map_name, version=version)
    for panel, lower in zip(axes, (False, True), strict=False):  # 1 panel on flat maps
        on_level = [
            point
            for point in points
            if is_lower_level(map_name, point[2] if len(point) > 2 else 0.0, version=version)
            == lower
        ]
        heatmap(
            map_name,
            on_level,
            method=method,
            bins=bins,
            cmap=cmap,
            alpha=alpha,
            bandwidth=bandwidth,
            version=version,
            lower=lower,
            ax=panel,
        )
    fig.tight_layout(pad=0.05)
    return fig, axes


# --- animation -------------------------------------------------------------------


def gif(
    map_name: str,
    frames: Sequence[Iterable[Player] | dict],
    path: str,
    *,
    fps: int = 2,
    version: int | None = None,
    lower: bool = False,
    dpi: int = 150,
) -> None:
    """Render a sequence of :func:`frame` calls to an animated GIF.

    Args:
        map_name: Map to draw, e.g. ``"de_inferno"``.
        frames: One entry per GIF frame — either an iterable of
            :class:`Player`, or a dict of :func:`frame` keyword arguments
            (e.g. ``{"players": [...], "bomb": (x, y, z)}``).
        path: Output ``.gif`` file path.
        fps: Frames per second.
        version: awpy-data release to use (default: newest cached).
        lower: Draw the lower-level radar of a multi-level map.
        dpi: Render resolution (150 → a 512px GIF).
    """
    from matplotlib.animation import PillowWriter

    fig, ax = plt.subplots(figsize=(RADAR_SIZE / 300, RADAR_SIZE / 300), dpi=dpi)
    writer = PillowWriter(fps=fps)
    try:
        with writer.saving(fig, path, dpi=dpi):
            for entry in frames:
                kwargs = dict(entry) if isinstance(entry, dict) else {"players": entry}
                ax.clear()
                frame(map_name, version=version, lower=lower, ax=ax, **kwargs)
                writer.grab_frame(facecolor="black")
    finally:
        plt.close(fig)
