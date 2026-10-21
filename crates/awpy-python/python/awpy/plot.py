"""Draw Counter-Strike 2 replay data with matplotlib and awpy-data.

Install the ``awpy[plot]`` extra. Map images and coordinate transforms come from
``awpy.data``. Set ``version=`` to select an awpy-data release.

Use ``frame`` for player state, ``heatmap`` for position density, and ``gif`` for
animations. Plot functions return matplotlib figures and axes for customization.

Examples:
    >>> from awpy import Demo, plot
    >>> demo = Demo("match.dem")
    >>> deaths = demo.kills.select("victim_x", "victim_y", "victim_z").rows()
    >>> fig, ax = plot.heatmap(demo.header["map_name"], deaths, method="kde")
    >>> fig.savefig("deaths.png")
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
    from matplotlib.transforms import Affine2D, ScaledTranslation, Transform
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    _msg = (
        "awpy.plot requires matplotlib -- install it with: "
        "uv add 'awpy[plot]' / pip install 'awpy[plot]'"
    )
    raise ImportError(_msg) from exc

from awpy import data
from awpy.map_control import LINE_OF_SIGHT_METHODS, MapControlParams, map_control_at

if TYPE_CHECKING:
    from awpy import Demo, NavMesh

__all__ = [
    "CONTESTED_COLOR",
    "CT_COLOR",
    "FIRE_RADIUS",
    "NAV_COLOR",
    "NAV_HIGHLIGHT_COLOR",
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
    "nav",
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


def _meta(map_name: str, version: int | None) -> dict[str, Any]:
    """Read a CS2 map coordinate transform and vertical sections.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        The map metadata dictionary from ``map_data.json``.
    """
    map_data = data.map_data(version)
    try:
        return map_data[map_name]
    except KeyError:
        tag = data.resolve_version(version)
        raise KeyError(f"no map data for '{map_name}' in {data.DATA_REPO} {tag}") from None


def world_to_pixel(map_name: str, point: Sequence[float], *, version: int | None = None) -> Point2:
    """Convert CS2 world coordinates to radar pixels.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        point: World or radar coordinates, as specified by the function.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        ``(px, py)`` pixels, with origin at the upper left and Y increasing downward.
    """
    meta = _meta(map_name, version)
    scale = meta["scale"]
    return (point[0] - meta["pos_x"]) / scale, (meta["pos_y"] - point[1]) / scale


def pixel_to_world(map_name: str, point: Sequence[float], *, version: int | None = None) -> Point2:
    """Convert radar pixels to CS2 world coordinates.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        point: World or radar coordinates, as specified by the function.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        ``(x, y)`` in Hammer units.
    """
    meta = _meta(map_name, version)
    scale = meta["scale"]
    return point[0] * scale + meta["pos_x"], meta["pos_y"] - point[1] * scale


def is_lower_level(map_name: str, z: float, *, version: int | None = None) -> bool:
    """Check whether a CS2 altitude belongs to the lower radar level.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        z: World altitude in Hammer units.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        Whether the altitude is in the lower section. False for a single-level map.
    """
    sections = _meta(map_name, version).get("verticalsections") or {}
    lower = sections.get("lower")
    if lower is None:
        return False
    return float(lower["AltitudeMin"]) <= z < float(lower["AltitudeMax"])


def has_lower_level(map_name: str, *, version: int | None = None) -> bool:
    """Check whether awpy-data defines a lower radar level.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        Whether the map defines a lower section.
    """
    sections = _meta(map_name, version).get("verticalsections") or {}
    return "lower" in sections


def _split_by_level(
    map_name: str,
    points: Iterable[Sequence[float]],
    *,
    lower: bool,
    version: int | None,
) -> tuple[list[float], list[float], int]:
    """Project positions onto one radar level.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        points: World ``(x, y)`` or ``(x, y, z)`` positions.
        lower: Select the lower-level radar.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        Pixel X values, pixel Y values, and the number of off-level points. Off-radar points are
        omitted.
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
    """Draw a CS2 radar image on matplotlib axes.

    Args:
        map_name: Map to draw, e.g. ``"de_inferno"``.
        version: awpy-data release to use (default: newest cached).
        lower: Draw the lower-level radar of a multi-level map.
        ax: Draw onto an existing axes instead of creating a new figure.

    Returns:
        The matplotlib ``(Figure, Axes)`` pair, with hidden axes and radar-pixel coordinates.
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
    """Set the drawing attributes for one CS2 player marker.

    Attributes:
        x: World X position in Hammer units.
        y: World Y position in Hammer units.
        z: World altitude in Hammer units; default 0.
        side: ``t`` or ``terrorist``, or ``ct`` or ``counter-terrorist``. Matching ignores case.
        hp: Health for the marker bar. Zero draws a dim death marker; ``None`` omits the bar.
        armor: Armor for the marker bar, or ``None`` to omit it.
        yaw: View direction in degrees, counterclockwise from positive X. ``None`` omits it.
        label: Text beside the marker, or ``None``.
        color: Matplotlib color override, or ``None`` to use the side color.
        has_bomb: Add a red border for the bomb carrier.
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
        """Select an explicit marker color or the CS2 side color.

        Returns:
            The matplotlib color string.
        """
        if self.color is not None:
            return self.color
        # Demo dataframes say "terrorist"/"counter-terrorist"; people say "t"/"ct".
        side = (self.side or "").lower()
        if side in ("ct", "counter-terrorist"):
            return CT_COLOR
        if side in ("t", "terrorist"):
            return T_COLOR
        return NEUTRAL_COLOR


def _marker_offset(ax: Axes, px: float, py: float) -> Transform:
    """Create a screen-point transform anchored at a player marker.

    Args:
        ax: Existing matplotlib axes, or ``None`` to create a figure.
        px: Radar pixel X coordinate.
        py: Radar pixel Y coordinate.

    Returns:
        A matplotlib transform with positive X right and positive Y down. Marker attachments retain
        their screen size when the axes or DPI changes.

    Raises:
        ValueError: If the axes are not attached to a figure.
    """
    fig = ax.get_figure(root=True)
    if fig is None:  # pragma: no cover - an Axes detached from any figure
        raise ValueError("ax is not attached to a figure")
    # Points -> inches (flipping y so +y is downward on screen), then
    # `dpi_scale_trans` for inches -> display pixels, then pin the origin to the
    # marker's (pixel-snapped) data position.
    #
    # The inches step must go through `dpi_scale_trans` rather than baking
    # `fig.dpi / 72` into the scale: `savefig(dpi=...)` temporarily overrides the
    # figure's dpi, and a baked factor would not follow it. The marker, label, and
    # yaw tick are all sized by matplotlib's own point handling, which does follow
    # it — so a frozen factor here makes the bars the wrong size relative to the
    # marker at any dpi other than the figure's own (they land *inside* the circle
    # when saving at a higher dpi). `dpi_scale_trans` is invalidated on a dpi
    # change, so composing with it keeps every piece in step.
    return (
        Affine2D().scale(1 / 72.0, -1 / 72.0)
        + fig.dpi_scale_trans
        + ScaledTranslation(
            round(px),
            round(py),
            ax.transData,  # ty: ignore[invalid-argument-type]
        )
    )


def _draw_player(ax: Axes, px: float, py: float, player: Player, alpha: float) -> None:
    """Draw one CS2 player marker and its labels.

    Args:
        ax: Existing matplotlib axes, or ``None`` to create a figure.
        px: Radar pixel X coordinate.
        py: Radar pixel Y coordinate.
        player: Player marker attributes.
        alpha: Opacity from 0 to 1.
    """
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
        # the fixed-size marker when zoomed in.
        #
        # The offset is in **display** space, where +y is up — not in radar-pixel
        # space, where +y is down. So the world facing vector `(cos, sin)` is used
        # as-is: negating the y component here mirrors the tick vertically, which
        # points every view direction at its reflection.
        dx = math.cos(math.radians(player.yaw))
        dy = math.sin(math.radians(player.yaw))
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
    """Convert a Hammer-unit radius to radar pixels.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        world_radius: Radius in Hammer units.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        The radius in radar pixels.
    """
    return world_radius / _meta(map_name, version)["scale"]


def _draw_area(
    ax: Axes, px: float, py: float, radius: float, color: str, alpha: float, zorder: int
) -> None:
    """Draw a smoke or fire disc on the radar.

    Args:
        ax: Existing matplotlib axes, or ``None`` to create a figure.
        px: Radar pixel X coordinate.
        py: Radar pixel Y coordinate.
        radius: Radius in radar pixels.
        color: Matplotlib color.
        alpha: Opacity from 0 to 1.
        zorder: Matplotlib drawing order.
    """
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
    """Draw a live grenade projectile on the radar.

    Args:
        ax: Existing matplotlib axes, or ``None`` to create a figure.
        px: Radar pixel X coordinate.
        py: Radar pixel Y coordinate.
        color: Matplotlib color.
        alpha: Opacity from 0 to 1.
    """
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
    """Resolve a grenade position and marker color.

    Args:
        entry: World position or a mapping with position and optional grenade type or color.

    Returns:
        The position and color, or ``None`` for an unsupported entry.
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
    """Draw CS2 players, bomb state, and projectiles with matplotlib.

    Args:
        map_name: CS2 map name.
        players: Player markers. Set ``has_bomb=True`` on the bomb carrier.
        bomb: World ``(x, y, z)`` bomb position, or ``None``. Drawn as an orange diamond.
        bomb_planted: Add a green border to the planted bomb.
        smokes: World ``(x, y)`` or ``(x, y, z)`` centers of active smoke clouds.
        fires: World ``(x, y)`` or ``(x, y, z)`` origins of active fires.
        grenades: Projectile positions or mappings with ``pos`` or ``x``/``y``/``z`` fields. A
            mapping can set ``type`` or ``color``. Include only rows at this tick.
        smoke_radius: Smoke radius in Hammer units; default 144.
        fire_radius: Fire radius in Hammer units; default 150.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.
        lower: Draw the lower-level radar.
        off_level_alpha: Opacity for markers on the other map level. Zero hides them.
        ax: Existing matplotlib axes, or ``None`` to create a figure.

    Returns:
        The matplotlib ``(Figure, Axes)`` pair.
    """
    fig, ax = radar(map_name, version=version, lower=lower, ax=ax)

    def _level_alpha(z: float) -> float:
        """Select marker opacity for the current radar level.

        Args:
            z: World altitude in Hammer units.

        Returns:
            Full opacity on this level, or the configured off-level opacity.
        """
        return 1.0 if is_lower_level(map_name, z, version=version) == lower else off_level_alpha

    def _in_bounds(px: float, py: float) -> bool:
        """Check whether a radar point is inside the image.

        Args:
            px: Radar pixel X coordinate.
            py: Radar pixel Y coordinate.

        Returns:
            Whether both coordinates are within the radar bounds.
        """
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
    """Create one matplotlib radar panel for each map level.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        The figure and a tuple of axes, upper level first.
    """
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
    """Draw CS2 player state on one panel per map level.

    Args:
        map_name: Map to draw, e.g. ``"de_nuke"``.
        players: A :class:`Player` per player to draw. Set ``has_bomb`` on the carrier to give its
            marker a red border.
        bomb: World ``(x, y, z)`` of the bomb, drawn as an orange diamond.
        bomb_planted: Give the bomb a green border to mark it planted and ticking.
        version: awpy-data release to use (default: newest cached).

    Returns:
        The figure and axes tuple. Two-level maps return upper and lower panels; single-level maps
        return one panel.
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

#: Fill color for nav areas drawn by :func:`nav` — a muted amber that reads as
#: "the walkable surface" without competing with the radar underneath.
NAV_COLOR = "#F5A524"
#: Fill color for the areas passed as ``highlight`` to :func:`nav`.
NAV_HIGHLIGHT_COLOR = "#22D3EE"


def _fill_nav_areas(
    ax: Axes,
    mesh: NavMesh,
    map_name: str,
    colors: Mapping[int, str],
    *,
    version: int | None,
    lower: bool,
    alpha: float,
    zorder: int = 4,
    edge: bool = False,
    linewidth: float = 0.4,
) -> int:
    """Fill navigation polygons on one radar level.

    Args:
        ax: Axes to draw on.
        mesh: The map's nav mesh.
        map_name: Map the axes is showing (for the world -> pixel transform).
        colors: Area id -> fill color. Areas absent from this mapping are skipped.
        version: awpy-data release, for the coordinate transform.
        lower: Whether ``ax`` is showing the lower level.
        alpha: Fill opacity.
        zorder: Draw order for the patches.
        edge: Outline each area in its fill color — this is what makes a mesh legible *as* a mesh
            rather than one flat blob.
        linewidth: Outline width when ``edge`` is set.

    Returns:
        The number of areas drawn.
    """
    drawn = 0
    for area_id, color in colors.items():
        info = mesh.area(int(area_id))
        if info is None or len(info["corners"]) < 3:
            continue
        if is_lower_level(map_name, info["centroid"][2], version=version) != lower:
            continue
        corners = [
            world_to_pixel(map_name, (cx, cy), version=version) for cx, cy, _ in info["corners"]
        ]
        ax.add_patch(
            Polygon(
                corners,
                closed=True,
                facecolor=color,
                edgecolor=color if edge else "none",
                linewidth=linewidth if edge else 0.0,
                alpha=alpha,
                zorder=zorder,
            )
        )
        drawn += 1
    return drawn


def nav(
    map_name: str,
    *,
    highlight: Sequence[int] | None = None,
    version: int | None = None,
    lower: bool = False,
    alpha: float = 0.25,
    edge: bool = True,
    legend: bool = True,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Draw CS2 navigation areas and selected routes.

    Args:
        map_name: Map to draw, e.g. ``"de_dust2"``.
        highlight: Area ids to emphasize in a contrasting color, drawn above the rest. Pass the
            result of :meth:`awpy.NavMesh.find_path` to show a route.
        version: awpy-data release to use (default: newest cached).
        lower: Draw the lower-level radar of a multi-level map. Areas are filtered to the level
            being drawn, so a two-level map needs one call per level (or use
            :func:`frame_levels`-style side-by-side axes).
        alpha: Fill opacity of the areas.
        edge: Outline each area, which is what makes the mesh legible as a mesh.
        legend: Label the area count (and highlighted count, if any).
        ax: Draw onto an existing axes instead of creating a new figure.

    Returns:
        The matplotlib ``(Figure, Axes)`` pair.
    """
    from awpy import NavMesh

    mesh = NavMesh(map_name, version=version)
    fig, ax = radar(map_name, version=version, lower=lower, ax=ax)

    marked = {int(a) for a in highlight or ()}
    base = {int(a): NAV_COLOR for a in mesh.areas["area_id"] if int(a) not in marked}
    drawn = _fill_nav_areas(
        ax, mesh, map_name, base, version=version, lower=lower, alpha=alpha, edge=edge
    )

    # Highlights go on top, at full strength — a route is the subject of the plot,
    # not part of the backdrop.
    highlighted = 0
    if marked:
        highlighted = _fill_nav_areas(
            ax,
            mesh,
            map_name,
            dict.fromkeys(marked, NAV_HIGHLIGHT_COLOR),
            version=version,
            lower=lower,
            alpha=min(1.0, alpha * 3),
            zorder=6,
            edge=edge,
            linewidth=0.8,
        )

    if legend:
        label = f"{drawn + highlighted} nav areas"
        # On a multi-level map the count is per level, so say which one — otherwise
        # it reads as the map's total.
        if has_lower_level(map_name, version=version):
            label += f" · {'lower' if lower else 'upper'} level"
        if highlighted:
            label += f" · {highlighted} highlighted"
        ax.text(
            0.5,
            0.985,
            label,
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=8,
            color="#E5E7EB",
        )
    return fig, ax


def map_control(
    demo: Demo,
    tick: int,
    *,
    method: Literal["raycast", "vision", "reachability"] = "vision",
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
    """Draw estimated CS2 map control at one demo tick.

    Args:
        demo: The parsed demo.
        tick: The tick to draw.
        method: ``"raycast"``, ``"vision"``, or ``"reachability"`` (see :mod:`awpy.map_control`).
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
        The matplotlib ``(Figure, Axes)`` pair.
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
    mesh = NavMesh(map_name, version=version)

    fig, ax = radar(map_name, version=version, lower=lower, ax=ax)

    # Fill each non-neutral area with its controlling side's color.
    _fill_nav_areas(
        ax,
        mesh,
        map_name,
        {
            int(area): _CONTROL_COLORS[label]
            for area, label in labels.items()
            if label in _CONTROL_COLORS
        },
        version=version,
        lower=lower,
        alpha=alpha,
    )

    if occluders:
        # Smokes shape both line-of-sight models; molotovs shape reachability.
        line_of_sight = method in LINE_OF_SIGHT_METHODS
        source = demo.smokes if line_of_sight else demo.fires
        color = _SMOKE_COLOR if line_of_sight else _FIRE_COLOR
        world_r = params.smoke_radius if line_of_sight else params.fire_radius
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
                # Carry everything the snapshot knows, so a player here reads the
                # same as one drawn by `frame` — armor included. `label` is left
                # off deliberately: ten names over shaded areas is unreadable.
                player = Player(
                    x=row["x"],
                    y=row["y"],
                    z=z,
                    side=row["side"],
                    hp=row["health"],
                    armor=row["armor"],
                    yaw=row["yaw"],
                    has_bomb=row["has_bomb"],
                )
                _draw_player(ax, px, py, player, 1.0)

    if legend:
        _map_control_legend(ax, control)
    return fig, ax


def _map_control_legend(ax: Axes, control: pl.DataFrame) -> None:
    """Draw each control label and its share of the map.

    Args:
        ax: Existing matplotlib axes, or ``None`` to create a figure.
        control: Per-area control rows.
    """
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
    """Smooth a density array with a separable Gaussian filter.

    Args:
        grid: Two-dimensional density array.
        sigma: Gaussian smoothing radius in grid cells.

    Returns:
        The smoothed density array.
    """
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
    """Draw CS2 position density over a radar image.

    Args:
        map_name: CS2 map name.
        points: World ``(x, y)`` or ``(x, y, z)`` positions.
        method: ``hex`` for hexagonal bins, ``hist`` for square bins, or ``kde`` for Gaussian
            smoothing.
        bins: Grid resolution for hexagonal and square bins. Gaussian smoothing uses a fixed grid.
        cmap: Matplotlib colormap name.
        alpha: Overlay opacity from 0 to 1.
        bandwidth: Gaussian smoothing width in radar pixels.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.
        lower: Draw the lower-level radar.
        ax: Existing matplotlib axes, or ``None`` to create a figure.

    Returns:
        The matplotlib ``(Figure, Axes)`` pair.

    Raises:
        ValueError: If the method is unknown.

    Notes:
        Positions on another radar level are omitted with a warning. Use ``heatmap_levels`` to draw
        all levels.
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
    """Draw CS2 position density on one panel per map level.

    Args:
        map_name: CS2 map name.
        points: World ``(x, y)`` or ``(x, y, z)`` positions.
        method: ``hex`` for hexagonal bins, ``hist`` for square bins, or ``kde`` for Gaussian
            smoothing.
        bins: Grid resolution for hexagonal and square bins. Gaussian smoothing uses a fixed grid.
        cmap: Matplotlib colormap name.
        alpha: Overlay opacity from 0 to 1.
        bandwidth: Gaussian smoothing width in radar pixels.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.

    Returns:
        The figure and axes tuple, upper level first. A single-level map returns one panel.

    Raises:
        ValueError: If the method is unknown.
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
    frames: Sequence[Iterable[Player] | dict[str, Any]],
    path: str,
    *,
    fps: int = 2,
    version: int | None = None,
    lower: bool = False,
    dpi: int = 150,
) -> None:
    """Save CS2 player-state frames as an animated GIF.

    Args:
        map_name: CS2 map name.
        frames: One player iterable or ``frame`` keyword dictionary for each output frame.
        path: Destination GIF file path.
        fps: Frames per second.
        version: awpy-data ClientVersion. Omit to use the newest cached release; an empty cache
            selects the latest release.
        lower: Draw the lower-level radar.
        dpi: Render resolution in dots per inch.
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
