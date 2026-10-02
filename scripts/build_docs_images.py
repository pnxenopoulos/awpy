"""Regenerate the figures embedded in the documentation.

The docs ship **pre-rendered** figures rather than building them, because a docs
build has neither a demo (the fixtures are opt-in and ~1.5 GB) nor the ~130 MB
awpy-data asset cache, and Sphinx runs with ``-W`` so any network hiccup would
fail CI. So: run this locally when a plot's appearance changes, and commit the
result.

    uv run --project crates/awpy-python python scripts/build_docs_images.py DEMO.dem

Every figure lands in ``crates/awpy-python/docs/img/``. Pass ``--only`` to
regenerate a subset while iterating on one plot.

Requires the plot extra (matplotlib) and a cached awpy-data release (``awpy get``).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import polars as pl
from awpy import Demo, NavMesh, VisibilityChecker, plot

# Render off-screen: this runs headless in a terminal, not in a notebook. Setting
# the backend after importing pyplot switches it, which is all we need.
matplotlib.use("Agg")

# Not under `_static`: Sphinx copies that verbatim *and* would copy referenced
# images into `_images/`, duplicating every figure in the built output.
OUT_DIR = Path(__file__).resolve().parents[1] / "crates/awpy-python/docs/img"

# `plot.radar` sizes its figure as `RADAR_SIZE / 300` inches, so **300 dpi is
# exactly the radar's native 1024px** and anything less throws resolution away.
# The docs render these at roughly a 700-900px column, so 600 dpi (~1900px) is
# about 2x that — crisp on a HiDPI display. Above native the radar bitmap is only
# upscaled, but the overlays (labels, markers, area outlines) are vector and do
# keep sharpening, which is what makes the difference on screen.
DPI = 600

# WebP rather than PNG: at this resolution PNG runs ~700KB a figure, and WebP is
# 80% smaller at a quality that is indistinguishable here. Sphinx does not list
# image/webp in `supported_image_types`, but that only governs wildcard candidate
# selection — an explicit `.webp` path builds clean under `-W` and every current
# browser renders it.
FORMAT = "webp"
WEBP_QUALITY = 90

#: Map used for the asset-only figures (nav meshes), independent of the demo.
NAV_MAP = "de_dust2"
#: Multi-level map for the per-level figures.
LEVELS_MAP = "de_nuke"


def _save(fig: plt.Figure, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.{FORMAT}"
    fig.savefig(
        path,
        dpi=DPI,
        bbox_inches="tight",
        facecolor="#0B0E14",
        pil_kwargs={"quality": WEBP_QUALITY, "method": 6} if FORMAT == "webp" else {},
    )
    plt.close(fig)
    from PIL import Image

    width, height = Image.open(path).size
    print(f"  {path.name:<32} {width:>5}x{height:<5} {path.stat().st_size / 1024:>6.0f} KB")


# --- nav.md --------------------------------------------------------------------


def nav_mesh() -> None:
    """The whole mesh over the radar."""
    fig, _ = plot.nav(NAV_MAP)
    _save(fig, "nav-mesh")


def nav_path() -> None:
    """A route across the mesh, from T spawn toward the A site."""
    mesh = NavMesh(NAV_MAP)
    start = mesh.find_area((-680.0, 1500.0, 0.0))
    end = mesh.find_area((1200.0, 2400.0, 0.0))
    if start is None or end is None:
        raise SystemExit(f"could not resolve path endpoints on {NAV_MAP}")
    route = mesh.find_path(start, end)
    print(f"    route: {len(route)} areas ({start} -> {end})")
    fig, _ = plot.nav(NAV_MAP, highlight=route)
    _save(fig, "nav-path")


# --- map_control.md ------------------------------------------------------------


def _busy_tick(demo: Demo) -> int:
    """A tick worth drawing: mid-round in the round with the most damage.

    Round starts are boring — everyone is still in spawn and the map is almost all
    neutral. Picking the busiest round and sampling partway through its live play
    gives a picture with actual contested territory in it.
    """
    rounds = demo.rounds.filter(~pl.col("is_knife_round"))
    damages = demo.damages
    best, best_count = None, -1
    for row in rounds.iter_rows(named=True):
        start = row["freeze_end_tick"] or row["start_tick"]
        if start is None:
            continue
        count = damages.filter(
            (pl.col("tick") >= start) & (pl.col("tick") <= row["end_tick"])
        ).height
        if count > best_count:
            best, best_count = row, count
    if best is None:
        raise SystemExit("no usable rounds in this demo")
    start = best["freeze_end_tick"] or best["start_tick"]
    # 40% into the round: engagements have started, nobody has won yet.
    tick = int(start + 0.4 * (best["end_tick"] - start))
    print(f"    round {best['round_num']} ({best_count} damage events) -> tick {tick}")
    return tick


def map_control_methods(demo: Demo) -> None:
    """The same moment under all three models, so the contrast is visible."""
    tick = _busy_tick(demo)
    for method in ("raycast", "vision", "reachability"):
        fig, _ = plot.map_control(demo, tick, method=method)
        _save(fig, f"map-control-{method}")


def map_control_cone(demo: Demo) -> None:
    """One player, both line-of-sight models, with the cone drawn on top.

    The team-level figures shade the union of five differently-pointed cones, each
    chopped up by geometry — which tells you nothing about what the model does. This
    isolates a single player so the 90-degree arc is legible, and overlays the yaw
    line and its two edges so the shading can be checked against them by eye.
    """
    import math

    from awpy._awpy import compute_map_control
    from awpy.plot import radar, world_to_pixel

    tick = _busy_tick(demo)
    map_name = demo.header["map_name"]
    mesh, vis = NavMesh(map_name), VisibilityChecker(map_name)

    # The player with the most to look at, so the picture is not a dead end.
    snap = demo.snapshots(ticks=tick).filter(pl.col("health") > 0).drop_nulls("yaw")
    best, best_seen = None, -1
    for row in snap.iter_rows(named=True):
        one = [(row["x"], row["y"], row["z"], "ct", False, False, row["yaw"])]
        held = compute_map_control(mesh, one, visibility=vis, method="vision", detail=True)
        seen = sum(c == "ct" for c in held["control"])
        if seen > best_seen:
            best, best_seen = row, seen
    if best is None:
        raise SystemExit("no player with a resolved yaw at this tick")

    origin = (best["x"], best["y"], best["z"])
    one = [(*origin, "ct", False, False, best["yaw"])]
    held = {}
    for method in ("raycast", "vision"):
        res = compute_map_control(mesh, one, visibility=vis, method=method, detail=True)
        pairs = zip(res["area_ids"], res["control"], strict=True)
        held[method] = {a for a, c in pairs if c == "ct"}
    print(
        f"    {best['name']} yaw={best['yaw']:.0f}deg  "
        f"raycast {len(held['raycast'])} areas, vision {len(held['vision'])}"
    )

    fig, ax = radar(map_name)
    # Raycast underneath in grey, vision on top in the highlight color, so the
    # difference between the two models is the difference between the two fills.
    _fill(ax, mesh, map_name, held["raycast"], "#6B7280", 0.5, 4)
    _fill(ax, mesh, map_name, held["vision"], plot.NAV_HIGHLIGHT_COLOR, 0.85, 6)

    px, py = world_to_pixel(map_name, origin)
    ax.scatter([px], [py], s=70, color=plot.T_COLOR, edgecolors="black", linewidths=0.8, zorder=12)
    for offset, style in ((0.0, "-"), (45.0, "--"), (-45.0, "--")):
        angle = math.radians(best["yaw"] + offset)
        far = (origin[0] + 4000 * math.cos(angle), origin[1] + 4000 * math.sin(angle))
        fx, fy = world_to_pixel(map_name, far)
        ax.plot([px, fx], [py, fy], style, color=plot.T_COLOR, lw=1.1, zorder=11)
    ax.text(
        0.5,
        0.985,
        "one player · grey = raycast · cyan = vision (90\u00b0 cone)",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#E5E7EB",
    )
    _save(fig, "map-control-cone")


def _fill(ax, mesh, map_name: str, area_ids, color: str, alpha: float, zorder: int) -> None:
    """Fill the given nav areas on ``ax``."""
    from awpy.plot import world_to_pixel
    from matplotlib.patches import Polygon

    for area_id in area_ids:
        info = mesh.area(int(area_id))
        if info is None or len(info["corners"]) < 3:
            continue
        corners = [world_to_pixel(map_name, c) for c in info["corners"]]
        ax.add_patch(
            Polygon(
                corners, closed=True, facecolor=color, edgecolor="none", alpha=alpha, zorder=zorder
            )
        )


# --- plot.md -------------------------------------------------------------------


def plot_radar() -> None:
    """The bare canvas."""
    fig, _ = plot.radar(NAV_MAP)
    _save(fig, "plot-radar")


def plot_frame(demo: Demo) -> None:
    """A game state: every player, plus the bomb if it is down."""
    tick = _busy_tick(demo)
    snap = demo.snapshots(ticks=tick)
    players = [
        plot.Player(
            x=r["x"],
            y=r["y"],
            z=r["z"],
            yaw=r["yaw"],
            hp=r["health"],
            armor=r["armor"],
            side=r["side"],
            label=r["name"],
            has_bomb=r["has_bomb"],
        )
        for r in snap.iter_rows(named=True)
        if r["x"] is not None
    ]
    fig, _ = plot.frame(demo.header["map_name"], players)
    _save(fig, "plot-frame")


def plot_heatmap(demo: Demo) -> None:
    """Where players die, over the whole match."""
    deaths = demo.kills.select("victim_x", "victim_y", "victim_z").drop_nulls().rows()
    print(f"    {len(deaths)} death positions")
    fig, _ = plot.heatmap(demo.header["map_name"], deaths, method="kde")
    _save(fig, "plot-heatmap")


def plot_levels() -> None:
    """A multi-level map, one panel per level.

    The demos on hand aren't recorded on a multi-level map, so positions are
    sampled from the map's own nav areas. That is enough to show the behavior these
    figures exist to illustrate: each point is drawn on the panel for the level its
    ``z`` puts it on.
    """
    mesh = NavMesh(LEVELS_MAP)
    areas = mesh.areas.sample(n=min(600, len(mesh)), seed=7)
    centroids = [
        (row["centroid_x"], row["centroid_y"], row["centroid_z"])
        for row in areas.iter_rows(named=True)
    ]

    # Five players per level, so both panels are populated and the split is the
    # point of the picture.
    upper = [c for c in centroids if not plot.is_lower_level(LEVELS_MAP, c[2])]
    lower = [c for c in centroids if plot.is_lower_level(LEVELS_MAP, c[2])]
    print(f"    {len(upper)} upper / {len(lower)} lower sampled areas")
    players = [
        plot.Player(x=x, y=y, z=z, side=side, hp=100, armor=100, label=f"{side}{i + 1}")
        for side, pts in (("ct", upper[::13][:5]), ("t", lower[::7][:5]))
        for i, (x, y, z) in enumerate(pts)
    ]
    fig, _ = plot.frame_levels(LEVELS_MAP, players)
    _save(fig, "plot-frame-levels")

    fig, _ = plot.heatmap_levels(LEVELS_MAP, centroids, method="hex")
    _save(fig, "plot-heatmap-levels")


FIGURES: dict[str, tuple[str, bool]] = {
    # name -> (page it appears on, needs a demo)
    "nav_mesh": ("nav", False),
    "nav_path": ("nav", False),
    "map_control_methods": ("map_control", True),
    "map_control_cone": ("map_control", True),
    "plot_radar": ("plot", False),
    "plot_frame": ("plot", True),
    "plot_heatmap": ("plot", True),
    "plot_levels": ("plot", False),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "demo",
        type=Path,
        nargs="?",
        help="a .dem file, for the figures derived from match data",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=sorted(FIGURES),
        help="regenerate only these figure groups",
    )
    args = parser.parse_args()

    wanted = args.only or sorted(FIGURES)
    needs_demo = [n for n in wanted if FIGURES[n][1]]
    if needs_demo and args.demo is None:
        parser.error(f"these need a demo: {', '.join(needs_demo)}")

    demo = None
    if needs_demo:
        print(f"parsing {args.demo.name} ...")
        started = time.monotonic()
        demo = Demo(args.demo)
        _ = demo.rounds  # warm the shared parse so timings below are honest
        print(f"  parsed in {time.monotonic() - started:.1f}s ({demo.header['map_name']})")

    for name in wanted:
        page, demo_needed = FIGURES[name]
        print(f"{name}  [{page}.md]")
        func = globals()[name]
        func(demo) if demo_needed else func()

    print(f"\nWrote to {OUT_DIR}")
    print("Commit the images — the docs build does not regenerate them.")


if __name__ == "__main__":
    sys.exit(main())
