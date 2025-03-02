"""Stuff."""

import importlib.resources
import itertools
import json
import logging
import math
import os
import pickle
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Literal, Self

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.axes import Axes
from matplotlib.collections import PatchCollection
from PIL import Image
from shapely import Point, Polygon
from tqdm import tqdm

from awpy.constants import (
    CROUCHING_ATTRIBUTE_FLAG,
    JUMP_HEIGHT,
    PLAYER_CROUCH_HEIGHT,
    PLAYER_EYE_LEVEL,
    PLAYER_HEIGHT,
    PLAYER_WIDTH,
)
from awpy.data.map_data import MAP_DATA
from awpy.nav import NAV_DATA, DynamicAttributeFlags, Nav, NavArea, PathResult
from awpy.plot.utils import game_to_pixel
from awpy.spawn import SPAWNS_DATA, Spawns
from awpy.vector import Vector3
from awpy.visibility import BVHNode, VisibilityChecker, load_vis_checker

print("Finished imports, starting script", flush=True)

print(NAV_DATA.keys())
SUPPORTED_MAPS = {
    "de_ancient",
    "de_anubis",
    "de_dust2",
    "de_inferno",
    "de_mirage",
    "de_nuke",
    "de_overpass",
    "de_train",
    # "de_vertigo",
}
GRANULARITIES = (
    "nom",
    "100",
    "200",
)

MeetingStyle = Literal["fine", "rough"]


@dataclass(frozen=True)
class PathPoints:
    start: Vector3
    end: Vector3


@dataclass(frozen=True)
class PathDistances:
    direct: float
    reversed: float


GranularityDistances = dict[str, PathDistances]

MapDistances = dict[PathPoints, GranularityDistances]

Distances = dict[str, MapDistances]


def plot_map(map_name: str) -> tuple[plt.Figure, Axes]:
    fig, ax = plt.subplots(figsize=(1024 / 300, 1024 / 300), dpi=300)

    image = f"{map_name}.png"

    map_is_lower = map_name.endswith("_lower")
    if map_is_lower:
        map_name = map_name.removesuffix("_lower")

    # Load and display the map
    with importlib.resources.path("awpy.data.maps", image) as map_img_path:
        map_bg = mpimg.imread(map_img_path)
        ax.imshow(map_bg, zorder=0, alpha=0.5)

    return fig, ax


def get_area_avg_z(area: NavArea) -> float:
    """Get the average z coordinate for an Area.

    Args:
        area (dict): to get the avg z coordinatefor.

    Returns:
        float: Average z coordinate of the area.
    """
    return sum(corner.z for corner in area.corners) / len(area.corners)


def get_z_cutoff_shift(map_name: str, avg_z: float) -> float:
    """Get the y shift needed to adjsut for potential z cutoff.

    Args:
        map_name (str): Map to consider
        avg_z (float): z value to consider

    Returns:
        float: Modifier for y values depending on z cutoff
    """
    if (
        map_name in MAP_DATA
        and "lower_level_max_units" in (current_map_data := MAP_DATA[map_name])
        and avg_z < current_map_data["lower_level_max_units"]
    ):
        return 1024
    return 0


def _plot_tiles(
    map_areas: dict[int, NavArea],
    map_name: str,
    axis: Axes,
    color: str = "yellow",
    facecolor: str = "None",
    zorder: int = 1,
    *,
    show_z: bool = False,
) -> None:
    if show_z:
        for area in map_areas.values():
            x, y, _ = game_to_pixel(map_name, area.centroid)
            axis.text(x, y, str(round(area.centroid.z)), fontsize=2, color="black", ha="center")
    axis.add_collection(
        PatchCollection(
            [
                patches.Polygon(
                    [game_to_pixel(map_name, (c.x, c.y, c.z))[0:2] for c in area.corners],
                )
                for area in map_areas.values()
            ],
            linewidth=1,
            edgecolor=color,
            facecolor=facecolor,
            zorder=zorder,
        ),
    )


def _plot_points(
    points: list[Vector3], map_name: str, axis: Axes, color: str = "green", marker_size: float = 5, marker: str = "o"
) -> None:
    for point in points:
        x, y, _ = game_to_pixel(map_name, point)
        axis.plot(
            x,
            y,
            marker=marker,
            color=color,
            markersize=marker_size,
            alpha=1.0,
            zorder=10,
        )


def _plot_connection(
    area1: NavArea,
    area2: NavArea,
    map_name: str,
    axis: Axes,
    *,
    with_arrows: bool = False,
    color: str = "red",
    lw: float = 0.3,
) -> None:
    x1, y1, _ = game_to_pixel(map_name, area1.centroid)
    x2, y2, _ = game_to_pixel(map_name, area2.centroid)
    axis.plot([x1, x2], [y1, y2], color=color, lw=lw)

    if with_arrows:
        axis.annotate(
            "",
            xy=(x2, y2),  # Arrow tip
            xytext=(x1, y1),  # Arrow base
            arrowprops={"arrowstyle": "->", "color": color, "lw": lw},
        )


def plot_map_connections(
    output_path: str | Path,
    map_areas: dict[int, NavArea],
    map_name: str = "de_ancient",
    dpi: int = 300,
    *,
    extra_areas: dict[int, NavArea] | None = None,
    with_arrows: bool = False,
    granularity: str = "nom",
) -> None:
    """Plot all navigation mesh tiles in a given map.

    Args:
        output_path (string): Path to the output folder
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar".
            Indicates if you want to use the SimpleRadar dark map type
        dpi (int): DPI of the resulting image

    Returns:
        None, saves .png
    """
    output_path = Path(output_path) / granularity
    Path(output_path).mkdir(exist_ok=True, parents=True)
    logging.info("Plotting connections for %s", map_name)
    try:
        fig, axis = plot_map(map_name)
    except FileNotFoundError:
        return
    fig.set_size_inches(19.2, 21.6)
    _plot_tiles(map_areas, map_name, axis)
    if extra_areas:
        _plot_tiles(extra_areas, map_name, axis, color="green")

    if granularity == "nom":
        for area in tqdm(map_areas.values(), desc="Plot area"):
            for connections_id in area.connections:
                if connections_id not in map_areas:
                    continue
                connection = map_areas[connections_id]
                _plot_connection(area, connection, map_name, axis, with_arrows=with_arrows)

    plt.savefig(
        os.path.join(output_path, f"connections_{map_name}_{granularity}.png"),
        bbox_inches="tight",
        dpi=dpi,
    )
    fig.clear()
    plt.close(fig)


def in_box(pos: Vector3) -> bool:
    return -1067 < pos.x < -920 and 671 < pos.y < 1126


@dataclass
class NewNavArea:
    corners: list[Vector3]
    orig_ids: set[int]
    dynamic_attribute_flags: DynamicAttributeFlags
    connections: set[int] = field(default_factory=set)
    ladders_above: list[int] = field(default_factory=list)
    ladders_below: list[int] = field(default_factory=list)
    area_id: int = 0

    def polygon(self) -> Polygon:
        return Polygon([(c.x, c.y) for c in self.corners])

    def distance(self, other: "NewNavArea") -> float:
        return self.polygon().centroid.distance(other.polygon().centroid)

    def requires_crouch(self) -> bool:
        return DynamicAttributeFlags(CROUCHING_ATTRIBUTE_FLAG) == self.dynamic_attribute_flags

    @cached_property
    def centroid(self) -> Vector3:
        """Calculates the centroid of the polygon defined by the corners.

        Returns:
            A Vector3 representing the centroid (geometric center) of the polygon.
        """
        if not self.corners:
            return Vector3(0, 0, 0)  # Return origin if no corners exist

        x_coords = [corner.x for corner in self.corners]
        y_coords = [corner.y for corner in self.corners]

        centroid_x = sum(x_coords) / len(self.corners)
        centroid_y = sum(y_coords) / len(self.corners)

        # Assume z is averaged as well for completeness
        z_coords = [corner.z for corner in self.corners]
        centroid_z = sum(z_coords) / len(self.corners)

        return Vector3(centroid_x, centroid_y, centroid_z)


def regularize_nav_areas(  # noqa: PLR0912, PLR0915
    nav_areas: dict[int, NavArea],
    grid_granularity: int,
    map_name: str,
) -> dict[int, NavArea]:
    print(f"Regularizing nav areas for {map_name}")
    # Collect all x,y coordinates over all nav areas
    xs: list[float] = []
    ys: list[float] = []
    area_polygons: dict[int, Polygon] = {}
    area_levels: dict[int, float] = {}
    vis_checker = load_vis_checker(map_name)

    # Precompute the 2D polygon projection and an average-z for each nav area.
    for area_id, area in nav_areas.items():
        pts = [(corner.x, corner.y) for corner in area.corners]
        poly = Polygon(pts)
        area_polygons[area_id] = poly
        avg_z = sum(corner.z for corner in area.corners) / len(area.corners)
        area_levels[area_id] = avg_z
        xs.extend(corner.x for corner in area.corners)
        ys.extend(corner.y for corner in area.corners)

    if not xs or not ys:
        return {}

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    cell_width = (max_x - min_x) / grid_granularity
    cell_height = (max_y - min_y) / grid_granularity

    # new nav areas will be keyed by tuple: (grid_row, grid_col, orig_id)
    # level is computed from the covering nav-areas via average z.
    new_cells: list[NewNavArea] = []

    # For each grid cell, test the center with all nav area polygons.
    # We'll use a tolerance to group z levels. Here, we round to 2 decimal places.
    for i in tqdm(range(grid_granularity), desc="Rows"):
        for j in tqdm(range(grid_granularity), desc="Cols", leave=False):
            # boundaries for cell (i, j): note 0,0 at min_x,min_y.
            cell_min_x = min_x + j * cell_width
            cell_min_y = min_y + i * cell_height
            cell_max_x = cell_min_x + cell_width
            cell_max_y = cell_min_y + cell_height
            center_x = (cell_min_x + cell_max_x) / 2
            center_y = (cell_min_y + cell_max_y) / 2
            center_point = Point(center_x, center_y)
            cell_poly = Polygon(
                [
                    (cell_min_x, cell_min_y),
                    (cell_max_x, cell_min_y),
                    (cell_max_x, cell_max_y),
                    (cell_min_x, cell_max_y),
                ]
            )

            primary_origs = {area_id for area_id, poly in area_polygons.items() if poly.contains(center_point)}

            extra_orig_ids: set[int] = set()
            for area_id, poly in area_polygons.items():
                if poly.intersects(cell_poly):
                    extra_orig_ids.add(area_id)

            if not primary_origs and not extra_orig_ids:
                continue

            primary_origs = primary_origs or {
                min(
                    extra_orig_ids,
                    key=lambda aid: area_polygons[aid].centroid.distance(center_point),
                )
            }

            for primary in primary_origs:
                cell_orig_ids = {primary}
                primary_z = area_levels[primary]
                for other in extra_orig_ids:
                    if other == primary:
                        continue
                    if abs(primary_z - area_levels[other]) <= JUMP_HEIGHT:
                        cell_orig_ids.add(other)
                rep_level = round(primary_z, 2)
                corners = [
                    Vector3(cell_min_x, cell_min_y, rep_level),
                    Vector3(cell_max_x, cell_min_y, rep_level),
                    Vector3(cell_max_x, cell_max_y, rep_level),
                    Vector3(cell_min_x, cell_max_y, rep_level),
                ]
                primary_area = nav_areas[primary]
                new_cells.append(
                    NewNavArea(
                        corners=corners,
                        orig_ids=cell_orig_ids,
                        ladders_above=primary_area.ladders_above,
                        ladders_below=primary_area.ladders_below,
                        dynamic_attribute_flags=primary_area.dynamic_attribute_flags,
                    )
                )

    new_nav_areas: dict[int, NewNavArea] = {}
    old_to_new_children: dict[int, set[int]] = defaultdict(set)
    for idx, new_cell in enumerate(new_cells):
        new_cell.area_id = idx
        new_nav_areas[idx] = new_cell
        for orig_id in new_cell.orig_ids:
            old_to_new_children[orig_id].add(idx)

    # Build connectivity based solely on the new cell's orig_ids.
    # For a new cell A with orig set A_orig, connect to new cell B with orig set B_orig if:
    # ∃ a in A_orig and b in B_orig with a == b or b in nav_areas[a].connections
    for idx_a, new_area in tqdm(new_nav_areas.items(), desc="Connections"):
        parent_areas = new_area.orig_ids
        for parent_area in parent_areas:
            siblings = old_to_new_children[parent_area]
            new_area.connections.update(sibling for sibling in siblings if sibling != idx_a)

    # Connect to reachable areas
    for area1 in tqdm(new_nav_areas.values(), desc="Adding connections by visibility and jumpability"):
        for area2 in new_nav_areas.values():
            if area1.area_id == area2.area_id or area2.area_id in area1.connections:
                continue
            if (
                (set(area1.ladders_above) & set(area2.ladders_below))
                or (set(area1.ladders_below) & set(area2.ladders_above))
                or (area1.centroid.can_jump_to(area2.centroid) and areas_walkable(area1, area2, vis_checker))
            ):
                area1.connections.add(area2.area_id)

    # Ensure old connections are maintained
    for a_idx, area_a in tqdm(nav_areas.items(), desc="Ensuring old connections"):
        children_of_a = old_to_new_children[a_idx]
        for neighbor_of_a_idx in area_a.connections:
            children_of_neighbor_of_a = old_to_new_children[neighbor_of_a_idx]

            neighbors_of_children_of_a: set[int] = set(children_of_a)
            for child_of_a in children_of_a:
                neighbors_of_children_of_a.update(new_nav_areas[child_of_a].connections)

            if children_of_neighbor_of_a & neighbors_of_children_of_a:
                continue

            pairs_of_children = [
                (child_of_a, child_of_neighbor_of_a)
                for child_of_a in children_of_a
                for child_of_neighbor_of_a in children_of_neighbor_of_a
            ]
            if not pairs_of_children:
                continue

            closest_childrens = sorted(
                pairs_of_children,
                key=lambda pair: new_nav_areas[pair[0]].distance(new_nav_areas[pair[1]]),
            )[:1]
            for closest_children in closest_childrens:
                new_nav_areas[closest_children[0]].connections.add(closest_children[1])

    return {
        idx: NavArea(
            area_id=idx,
            corners=area.corners,
            connections=list(area.connections),
            ladders_above=area.ladders_above,
            ladders_below=area.ladders_below,
            dynamic_attribute_flags=area.dynamic_attribute_flags,
        )
        for idx, area in new_nav_areas.items()
    }


def _plot_path(
    path: list[NavArea],
    axis: Axes,
    map_name: str,
    color: str = "green",
    lw: float = 0.3,
    linestyle: str = "solid",
) -> None:
    for first, second in itertools.pairwise(path):
        x1, y1, _ = game_to_pixel(map_name, first.centroid)
        x2, y2, _ = game_to_pixel(map_name, second.centroid)
        axis.plot([x1, x2], [y1, y2], color=color, lw=lw, linestyle=linestyle)


def plot_path(
    map_name: str,
    map_nav: Nav,
    start: Vector3,
    end: Vector3,
    output_dir: str | Path,
    granularity: str = "nom",
    dpi: int = 300,
    weight: Literal["dist", "time_adjusted"] = "time_adjusted",
) -> tuple[float, float]:
    output_dir = Path(output_dir) / map_name / granularity
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    try:
        fig, axis = plot_map(map_name)
    except FileNotFoundError:
        return float("inf"), float("inf")
    fig.set_size_inches(19.2, 21.6)
    start_area = map_nav.find_area(start) or map_nav.find_closest_area_centroid(start)
    end_area = map_nav.find_area(end) or map_nav.find_closest_area_centroid(end)

    if not start_area or not end_area:
        print(f"Didnt find start {start_area}-{start} or end area {end_area}-{end}")
        return float("inf"), float("inf")

    _plot_tiles({0: start_area}, map_name, axis, color="green")
    _plot_tiles({1: end_area}, map_name, axis, color="red")
    _plot_points([start, end], map_name, axis)
    shortest_path, direct_distance = map_nav.find_path(start_area.area_id, end_area.area_id, weight=weight)
    shortest_path_reversed, reversed_distance = map_nav.find_path(end_area.area_id, start_area.area_id, weight=weight)
    print(f"Distances between {start_area.area_id}-{start} and {end_area.area_id}-{end}")
    print(f"Direct distance: {direct_distance}")
    print(f"Reversed distance: {reversed_distance}", flush=True)

    _plot_path(shortest_path, axis, map_name, color="green")
    _plot_path(shortest_path_reversed, axis, map_name, color="red")

    plt.savefig(
        os.path.join(
            output_dir,
            f"path_{map_name}_{start_area.area_id}_{end_area.area_id}_{granularity}.png",
        ),
        bbox_inches="tight",
        dpi=dpi,
    )
    fig.clear()
    plt.close(fig)
    return direct_distance, reversed_distance


def check_straight_and_reversed_distance(
    distances: PathDistances, map_name: str, path_points: PathPoints, granularity: str
) -> None:
    if distances.reversed == 0:
        print(f"At map: {map_name} for path: {path_points} and granularity {granularity} the reversed distance was 0.")
        print(f"Direct: {distances.direct}; Reversed: {distances.reversed}")
        return
    deviation = abs((distances.direct / distances.reversed) - 1)
    if deviation > 0.05:
        print(
            f"At map: {map_name} for path: {path_points} and granularity {granularity}"
            " the distances in both directions are not close."
        )

        print(f"Deviation: {deviation}; Direct: {distances.direct}; Reversed: {distances.reversed}")


def check_100_200_distances(
    dist_100: PathDistances,
    dist_200: PathDistances,
    map_name: str,
    path_points: PathPoints,
) -> None:
    if dist_100.direct == 0 or dist_200.direct == 0:
        return
    deviation_direct = abs((dist_100.direct / dist_200.direct) - 1)
    if deviation_direct > 0.05:
        print(f"At map: {map_name} for path: {path_points} between the 100 and 200 granularity are not close.")

        print(f"Deviation: {deviation_direct}; 100: {dist_100.direct}; 200: {dist_200.direct}")


def de_ancient_spawns() -> list[Vector3]:
    ct_spawn = Vector3(-256, 1590, 86)
    t_spawn = Vector3(-560, -2269, -98)
    return [ct_spawn, t_spawn]


def de_ancient_meetings() -> list[Vector3]:
    a_site = Vector3(-1790, -198, 136)
    mid = Vector3(-506, -297, 119)
    cave = Vector3(450, -276, 231)
    b_site = Vector3(1233, -417, 117)
    return [a_site, mid, cave, b_site]


def de_anubis_spawns() -> list[Vector3]:
    ct_spawn = Vector3(-476, 2216, 88)
    t_spawn = Vector3(-202, -1575, 52)
    mid = Vector3(-166, 455, 64)

    return [ct_spawn, t_spawn, mid]


def de_anubis_meetings() -> list[Vector3]:
    a_site = Vector3(1596, 972, -88)
    mid = Vector3(-166, 455, 64)
    water = Vector3(410, 122, -85)
    b_site = Vector3(-1500, 464, 63)
    tarp = Vector3(1410, 350, 64)
    tarp2 = Vector3(1301.03, 329.97, 63.89)
    tarp3 = Vector3(1283.45, 489.03, 65.87)
    return [a_site, mid, water, b_site, tarp, tarp2, tarp3]


def de_dust2_spawns() -> list[Vector3]:
    ct_spawn = Vector3(160, 2230, -61)
    t_spawn = Vector3(-590, -837, 176)
    return [ct_spawn, t_spawn]


def de_dust2_meetings() -> list[Vector3]:
    b_site = Vector3(-1992, 1690, 94)
    mid = Vector3(-389, 965, 14)
    long = Vector3(870, 972, 64)
    short = Vector3(367, 2265, 160)
    return [b_site, mid, long, short]


def de_inferno_spawns() -> list[Vector3]:
    ct_spawn = Vector3(2472, 2005, 198)
    t_spawn = Vector3(-1646, 321, 0)
    mid = Vector3(476, 585, 148)
    return [ct_spawn, t_spawn, mid]


def de_inferno_meetings() -> list[Vector3]:
    b_site = Vector3(40, 2837, 225)
    mid = Vector3(476, 585, 148)
    second = Vector3(467, -132, 133)
    apps = Vector3(1434, -286, 320)
    return [b_site, mid, second, apps]


def de_mirage_spawns() -> list[Vector3]:
    ct_spawn = Vector3(-1776, -1800, -203)
    t_spawn = Vector3(1278, -350, -104)
    a_site = Vector3(-252.69, -2065.91, 26.87)
    return [ct_spawn, t_spawn, a_site]


def de_mirage_meetings() -> list[Vector3]:
    apps = Vector3(-1462, 734, 16)
    short = Vector3(-822, -14, -105)
    mid = Vector3(91, -682, -112)
    conn = Vector3(-663, -1152, -104)
    ramp = Vector3(335, -1565, -121)
    palace = Vector3(443, -2292, 24)
    balcony = Vector3(-28.80, -2110.89, 23.87)
    return [apps, short, mid, conn, ramp, palace, balcony]


def de_nuke_spawns() -> list[Vector3]:
    ct_spawn = Vector3(2512, -504, -284)
    t_spawn = Vector3(-1816, -1223, -352)
    return [ct_spawn, t_spawn]


def de_nuke_meetings() -> list[Vector3]:
    ramp = Vector3(494, 115, -352)
    hut = Vector3(439, -1162, -328)
    squeaky = Vector3(135, -1325, -352)
    secret = Vector3(1220, -2389, -352)
    b_site = Vector3(665, -884, -708)
    return [ramp, hut, squeaky, secret, b_site]


def de_overpass_spawns() -> list[Vector3]:
    ct_spawn = Vector3(-2200, 740, 540)
    t_spawn = Vector3(-1338, -3138, 320)
    heaven = Vector3(-1693.83, 485.76, 323.86)
    return [ct_spawn, t_spawn, heaven]


def de_overpass_meetings() -> list[Vector3]:
    long = Vector3(-3730, -1782, 548)
    bath = Vector3(-2522, -888, 500)
    squeaky = Vector3(-1748, -1034, 164)
    short = Vector3(-1258, -966, 70)
    monster = Vector3(-498, -454, 82)
    return [long, bath, squeaky, short, monster]


def de_train_spawns() -> list[Vector3]:
    ct_spawn = Vector3(1493, -1269, -264)
    t_spawn = Vector3(-2029, 1382, -108)
    ct_spawn2 = Vector3(1626.8, -1498.7, -264)
    return [ct_spawn, t_spawn, ct_spawn2]


def de_train_meetings() -> list[Vector3]:
    ivy = Vector3(1034, 1497, -152)
    a_site = Vector3(391, 109, -152)
    pop = Vector3(-901, -308, -149)
    b_halls = Vector3(-987, -1004, -90)
    oil = Vector3(265.37, -1549.95, -113.13)
    upper = Vector3(-173.73, -1653.94, -103.13)
    halls_drop = Vector3(-976, -455, 82)
    hall_after_drop = Vector3(-978, -604, 24.5)
    return [ivy, a_site, pop, b_halls, oil, upper, halls_drop, hall_after_drop]


@dataclass
class SpawnDistance:
    area: NavArea
    distance: float
    path: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            area=NavArea.from_dict(data["area"]),
            distance=data["distance"],
            path=data["path"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area.to_dict(),
            "distance": self.distance,
            "path": self.path,
        }


@dataclass
class SpawnDistances:
    CT: list[SpawnDistance]
    T: list[SpawnDistance]

    @classmethod
    def from_json(cls, path: str | Path) -> Self:
        """Reads the navigation mesh data from a JSON file.

        Args:
            path: Path to the JSON file to read from.
        """
        spawn_distances_dict = json.loads(Path(path).read_text())
        return cls(
            CT=[SpawnDistance.from_dict(spawn_distance) for spawn_distance in spawn_distances_dict["CT"]],
            T=[SpawnDistance.from_dict(spawn_distance) for spawn_distance in spawn_distances_dict["T"]],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "CT": [spawn_distance.to_dict() for spawn_distance in self.CT],
            "T": [spawn_distance.to_dict() for spawn_distance in self.T],
        }

    def to_json(self, path: str | Path) -> None:
        """Writes the navigation mesh data to a JSON file.

        Args:
            path: Path to the JSON file to write.
        """
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(self.to_dict(), json_file)
            json_file.write("\n")


@dataclass
class SpreadResult:
    new_marked_areas_ct: set[int]
    new_marked_areas_t: set[int]

    visibility_connections: list[tuple[SpawnDistance, SpawnDistance]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            new_marked_areas_ct=set(data["new_marked_areas_ct"]),
            new_marked_areas_t=set(data["new_marked_areas_t"]),
            visibility_connections=[
                (SpawnDistance.from_dict(origin), SpawnDistance.from_dict(target))
                for origin, target in data["visibility_connections"]
            ],
        )

    @classmethod
    def list_from_json(cls, path: str | Path) -> list[Self]:
        return [cls.from_dict(entry) for entry in json.loads(Path(path).read_text())]


def get_distances_from_spawns(map_areas: Nav, spawns: Spawns) -> SpawnDistances:
    ct_distances: list[SpawnDistance] = []
    t_distances: list[SpawnDistance] = []
    for area in tqdm(map_areas.areas.values()):
        ct_path = min(
            (map_areas.find_path(spawn_point, area.area_id, weight="time_adjusted") for spawn_point in spawns.CT),
            default=PathResult(distance=float("inf"), path=[]),
            key=lambda path_result: path_result.distance,
        )
        t_path = min(
            (map_areas.find_path(spawn_point, area.area_id, weight="time_adjusted") for spawn_point in spawns.T),
            default=PathResult(distance=float("inf"), path=[]),
            key=lambda path_result: path_result.distance,
        )
        ct_distances.append(
            SpawnDistance(
                area=area,
                distance=ct_path.distance,
                path=[area.area_id for area in ct_path.path],
            )
        )
        t_distances.append(
            SpawnDistance(
                area=area,
                distance=t_path.distance,
                path=[area.area_id for area in t_path.path],
            )
        )
    return SpawnDistances(
        CT=sorted(ct_distances, key=lambda spawn_distance: spawn_distance.distance),
        T=sorted(t_distances, key=lambda spawn_distance: spawn_distance.distance),
    )


def areas_walkable(
    area1: NavArea | NewNavArea,
    area2: NavArea | NewNavArea,
    vis_checker: VisibilityChecker,
) -> bool:
    height = PLAYER_CROUCH_HEIGHT if (area1.requires_crouch() or area2.requires_crouch()) else PLAYER_HEIGHT
    width = 0.9 * PLAYER_WIDTH

    dx = area2.centroid.x - area1.centroid.x
    dy = area2.centroid.y - area1.centroid.y
    angle = math.atan2(dy, dx)

    for width_correction in (width / 2, -width / 2):
        dx_corr = width_correction * math.cos(angle)
        dy_corr = width_correction * math.sin(angle)
        used_centroid1 = Vector3(area1.centroid.x + dx_corr, area1.centroid.y + dy_corr, area1.centroid.z + height)
        used_centroid2 = Vector3(area2.centroid.x + dx_corr, area2.centroid.y + dy_corr, area2.centroid.z + height)
        if not vis_checker.is_visible(used_centroid1, used_centroid2):
            return False
    return True


def areas_visible(
    area1: NavArea | NewNavArea,
    area2: NavArea | NewNavArea,
    vis_checker: VisibilityChecker,
    *,
    correct_height: bool = False,
) -> bool:
    height_correction = PLAYER_EYE_LEVEL if correct_height else PLAYER_EYE_LEVEL / 2
    used_centroid1 = Vector3(area1.centroid.x, area1.centroid.y, area1.centroid.z + height_correction)
    used_centroid2 = Vector3(area2.centroid.x, area2.centroid.y, area2.centroid.z + height_correction)
    return vis_checker.is_visible(used_centroid1, used_centroid2)


def newly_visible(
    current_area: SpawnDistance,
    previous_opposing_areas: list[SpawnDistance],
    vis_checker: VisibilityChecker,
    *,
    own_spotted_areas: set[int],
    opposing_spotted_areas: set[int],
    style: MeetingStyle = "fine",
) -> list[SpawnDistance]:
    # Fine is the semantically correct one.
    # For every area we take the first time that a player who goes and waits there can be seen.
    if style == "fine":
        return [
            opposing_area
            for opposing_area in previous_opposing_areas
            if not (
                current_area.area.area_id in own_spotted_areas and opposing_area.area.area_id in opposing_spotted_areas
            )
            and areas_visible(current_area.area, opposing_area.area, vis_checker)
        ]
    # Rough
    # Here if an part of the path has been seen at any time we exclude the area.
    # This means that we might not correctly mark areas (particularly D2 B-site CTs)
    # But it significantly reduces the number of lines and for most maps structures
    # it should be enough.
    results: list[SpawnDistance] = []
    if any(path_id in own_spotted_areas for path_id in current_area.path):
        return []
    for opposing_area in sorted(previous_opposing_areas, key=lambda area: area.distance):
        if areas_visible(current_area.area, opposing_area.area, vis_checker):
            own_spotted_areas.add(current_area.area.area_id)
            opposing_spotted_areas.add(opposing_area.area.area_id)
            results.append(opposing_area)
    return results


def round_up_to_next_100(n: float) -> int:
    return math.ceil(n / 100) * 100


def _plot_visibility_connection(
    area1: SpawnDistance,
    area2: SpawnDistance,
    map_nav: Nav,
    map_name: str,
    axis: Axes,
    *,
    color: str = "red",
    lw: float = 1.0,
    highlight_area1: bool = False,
) -> None:
    if highlight_area1:
        _plot_points([area1.area.centroid], map_name, axis, color="yellow")
    _plot_tiles({0: area1.area, 1: area2.area}, map_name, axis, color=color)
    _plot_connection(area1.area, area2.area, map_name, axis, with_arrows=False, color=color, lw=lw)
    _plot_path(
        [map_nav.areas[path_id] for path_id in area1.path],
        axis,
        map_name,
        color=color,
        linestyle="dashed",
        lw=lw,
    )
    _plot_path(
        [map_nav.areas[path_id] for path_id in area2.path],
        axis,
        map_name,
        color=color,
        linestyle="dashed",
        lw=lw,
    )


def _get_triangles(node: BVHNode | None) -> list[NavArea]:
    if not node:
        return []
    if node.triangle:
        return [NavArea(corners=[node.triangle.p1, node.triangle.p2, node.triangle.p3])]
    return _get_triangles(node.left) + _get_triangles(node.right)


def _plot_node(node: BVHNode, axis: Axes, map_name: str) -> None:
    triangles = _get_triangles(node)
    _plot_tiles(
        dict(enumerate(triangles)),
        map_name=map_name,
        axis=axis,
        color="blue",
        zorder=4,
    )


def _plot_collision_triangles(map_name: str, axis: Axes, vis_checker: VisibilityChecker) -> None:
    _plot_node(vis_checker.root, axis, map_name)


def plot_triangles(*, with_clipping: bool = False) -> None:
    print("Plotting triangles.", flush=True)
    suffix = "-clippings" if with_clipping else ""
    for map_name in SUPPORTED_MAPS:
        print(f"Plotting triangles for {map_name}.", flush=True)
        output_dir = Path("triangles")
        output_dir.mkdir(exist_ok=True, parents=True)

        vis_checker = load_vis_checker(map_name, suffix=suffix)

        try:
            fig, axis = plot_map(map_name)
        except FileNotFoundError:
            continue
        fig.set_size_inches(19.2, 21.6)

        if map_name == "de_dust2":
            x1, y1, _ = game_to_pixel(map_name, Vector3(x=195.87492752075195, y=2467.874755859375, z=-52.5000057220459))
            x2, y2, _ = game_to_pixel(
                map_name, Vector3(x=-659.0001831054688, y=-766.5000813802084, z=188.00001525878906)
            )
            axis.plot([x1, x2], [y1, y2], color="red", lw=1.0)

            x1, y1, _ = game_to_pixel(map_name, Vector3(x=195.87492752075195, y=2467.874755859375, z=-52.5000057220459))
            x2, y2, _ = game_to_pixel(
                map_name, Vector3(x=-750.2501831054688, y=-790.8750915527344, z=187.00001525878906)
            )
            axis.plot([x1, x2], [y1, y2], color="red", lw=1.0)

        _plot_collision_triangles(map_name, axis, vis_checker)

        if map_name == "de_dust2":
            _plot_tiles(
                {
                    0: NavArea(
                        corners=[
                            Vector3(x=-621.9393310546875, y=-638.685302734375, z=262.0000305175781),
                            Vector3(x=-626.3272705078125, y=-638.685302734375, z=262.0000305175781),
                            Vector3(x=-626.3272705078125, y=-638.685302734375, z=134.0),
                        ]
                    ),
                },
                map_name=map_name,
                axis=axis,
                color="yellow",
                zorder=20,
            )

        plt.savefig(
            output_dir / f"triangles_{map_name}{suffix}.png",
            bbox_inches="tight",
            dpi=300,
        )
        fig.clear()
        plt.close(fig)


def plot_spread_from_input(map_name: str, granularity: str, style: MeetingStyle, nav: Nav) -> None:
    print("Loading spread input.", flush=True)
    spread_input = SpreadResult.list_from_json(Path("awpy/data") / f"{map_name}_{style}_spreads_{granularity}.json")
    print("Finished loading spread input.", flush=True)
    marked_areas_ct: set[int] = set()
    marked_areas_t: set[int] = set()

    output_dir = Path("spread") / map_name / style / granularity
    output_dir.mkdir(exist_ok=True, parents=True)

    for idx, spread_point in enumerate(tqdm(spread_input, desc="Plotting spreads.")):
        contains_new_connection = bool(spread_point.visibility_connections)
        new_conn_str = "_new" if contains_new_connection else ""

        try:
            fig, axis = plot_map(map_name)
        except FileNotFoundError:
            return
        fig.set_size_inches(19.2, 21.6)

        _plot_tiles(
            {area_id: nav.areas[area_id] for area_id in (marked_areas_ct | marked_areas_t)},
            map_name=map_name,
            axis=axis,
            color="olive",
        )
        _plot_tiles(
            {
                area_id: nav.areas[area_id]
                for area_id in (spread_point.new_marked_areas_ct | spread_point.new_marked_areas_t)
            },
            map_name=map_name,
            axis=axis,
            color="green",
        )

        _plot_tiles(
            {
                area_id: nav.areas[area_id]
                for area_id in (marked_areas_t | spread_point.new_marked_areas_t)
                & (marked_areas_ct | spread_point.new_marked_areas_ct)
            },
            map_name=map_name,
            axis=axis,
            color="purple",
        )
        marked_areas_ct |= spread_point.new_marked_areas_ct
        marked_areas_t |= spread_point.new_marked_areas_t
        _plot_tiles(
            {
                area_id: area
                for area_id, area in nav.areas.items()
                if area_id not in marked_areas_ct and area_id not in marked_areas_t
            },
            map_name=map_name,
            axis=axis,
            color="yellow",
        )

        for area1, area2 in spread_point.visibility_connections:
            _plot_visibility_connection(
                area1, area2, nav, map_name, axis, color="red", lw=1.0, highlight_area1=style == "rough"
            )

        plt.savefig(
            output_dir / f"spread_{map_name}_{granularity}{new_conn_str}_{idx}.png",
            bbox_inches="tight",
            dpi=300,
        )
        fig.clear()
        plt.close(fig)


def plot_spread(map_name: str, granularity: str, style: MeetingStyle = "fine") -> None:  # noqa: PLR0915
    print("Plotting spreads.", flush=True)
    target_dir = Path(f"awpy/data/nav_{granularity}")
    target_path = target_dir / f"{map_name}.json"
    nav = Nav.from_json(target_path)
    spawns = SPAWNS_DATA[map_name]
    spawn_distances_path = Path("awpy/data") / f"{map_name}_spawn_distances_{granularity}.json"

    vis_checker = load_vis_checker(map_name)

    if spawn_distances_path.is_file():
        spawn_distances = SpawnDistances.from_json(spawn_distances_path)
    else:
        spawn_distances = get_distances_from_spawns(nav, spawns)
        spawn_distances.to_json(spawn_distances_path)

    ct_index = 0
    marked_areas_ct: set[int] = set()
    marked_areas_t: set[int] = set()
    new_marked_areas_ct: set[int] = set()
    new_marked_areas_t: set[int] = set()
    t_index = 0
    output_dir = Path("spread") / map_name / style / granularity
    output_dir.mkdir(exist_ok=True, parents=True)

    last_plotted = float("-inf")

    visibility_connections: list[tuple[SpawnDistance, SpawnDistance]] = []
    spotted_areas_t: set[int] = set()
    spotted_areas_ct: set[int] = set()

    while True:
        if (current_ct_area := spawn_distances.CT[ct_index]).distance < (
            current_t_area := spawn_distances.T[t_index]
        ).distance:
            current_area = current_ct_area
            new_marked_areas_ct.add(current_ct_area.area.area_id)
            opposing_spotted_areas = spotted_areas_t
            own_spotted_areas = spotted_areas_ct
            opposing_previous_areas = [
                area for area in spawn_distances.T if area.area.area_id in (marked_areas_t | new_marked_areas_t)
            ]
            ct_index += 1
        else:
            current_area = current_t_area
            new_marked_areas_t.add(current_t_area.area.area_id)
            opposing_spotted_areas = spotted_areas_ct
            own_spotted_areas = spotted_areas_t
            opposing_previous_areas = [
                area for area in spawn_distances.CT if area.area.area_id in (marked_areas_ct | new_marked_areas_ct)
            ]
            t_index += 1

        print(current_area.area.area_id, flush=True)

        if current_area.distance == float("inf"):
            print(ct_index, t_index, current_area.distance)
            break

        if any(path_id in own_spotted_areas for path_id in current_area.path[-2:]):
            own_spotted_areas.add(current_area.area.area_id)

        visible_areas = newly_visible(
            current_area,
            opposing_previous_areas,
            vis_checker=vis_checker,
            own_spotted_areas=own_spotted_areas,
            opposing_spotted_areas=opposing_spotted_areas,
            style=style,
        )

        if visible_areas:
            own_spotted_areas.add(current_area.area.area_id)
            for spotted_by_area in visible_areas:
                opposing_spotted_areas.add(spotted_by_area.area.area_id)
                visibility_connections.append((current_area, spotted_by_area))

        if not (visible_areas or current_area.distance > (last_plotted + 100)):
            continue

        last_plotted = round_up_to_next_100(current_area.distance)

        try:
            fig, axis = plot_map(map_name)
        except FileNotFoundError:
            return
        fig.set_size_inches(19.2, 21.6)

        _plot_tiles(
            {area_id: nav.areas[area_id] for area_id in (marked_areas_ct | marked_areas_t)},
            map_name=map_name,
            axis=axis,
            color="olive",
        )
        _plot_tiles(
            {area_id: nav.areas[area_id] for area_id in (new_marked_areas_ct | new_marked_areas_t)},
            map_name=map_name,
            axis=axis,
            color="green",
        )

        _plot_tiles(
            {
                area_id: nav.areas[area_id]
                for area_id in (marked_areas_t | new_marked_areas_t) & (marked_areas_ct | new_marked_areas_ct)
            },
            map_name=map_name,
            axis=axis,
            color="purple",
        )
        marked_areas_ct |= new_marked_areas_ct
        marked_areas_t |= new_marked_areas_t
        new_marked_areas_ct.clear()
        new_marked_areas_t.clear()
        _plot_tiles(
            {
                area_id: area
                for area_id, area in nav.areas.items()
                if area_id not in marked_areas_ct and area_id not in marked_areas_t
            },
            map_name=map_name,
            axis=axis,
            color="yellow",
        )

        for area1, area2 in visibility_connections:
            _plot_visibility_connection(
                area1, area2, nav, map_name, axis, color="red", lw=1.0, highlight_area1=style == "rough"
            )

        plt.savefig(
            output_dir / f"spread_{map_name}_{granularity}_{current_area.distance}.png",
            bbox_inches="tight",
            dpi=300,
        )
        fig.clear()
        plt.close(fig)


def generate_spread_gif(map_name: str, granularity: str, style: MeetingStyle) -> None:
    output_dir = Path("spread") / map_name / style / granularity
    num_pattern = re.compile(r"_([\d\.]+)\.png$")

    # Function to extract the number from filename
    def extract_number(filename: Path) -> float:
        match = num_pattern.search(filename.name)
        return float(match.group(1)) if match else float("inf")

    image_files = sorted(output_dir.glob("*.png"), key=extract_number)

    # Open images and convert them to a list of frames
    frames = [Image.open(img) for img in image_files]

    if frames:
        frames[0].save(output_dir / "spread.gif", save_all=True, append_images=frames[1:], duration=200, disposal=2)
        print(f"GIF saved at {output_dir / 'spread.gif'}")
    else:
        print("No PNG files found in the directory.")


def generate_grids() -> None:
    print("Generating grids.", flush=True)
    for granularity in GRANULARITIES:
        print(f"Grid {granularity}:")
        target_dir = Path(f"awpy/data/nav_{granularity}")
        target_dir.mkdir(exist_ok=True, parents=True)

        for map_name in SUPPORTED_MAPS:
            print(f"At map: {map_name}")

            target_path = target_dir / f"{map_name}.json"
            if target_path.is_file():
                modified_nav = Nav.from_json(target_path)
            else:
                map_areas = regularize_nav_areas(
                    NAV_DATA[map_name].areas, grid_granularity=int(granularity), map_name=map_name
                )
                modified_nav = Nav(areas=map_areas)
                modified_nav.to_json(target_path)

            plot_map_connections(
                "connections",
                modified_nav.areas,
                map_name=map_name,
                extra_areas={} if granularity == "nom" else NAV_DATA[map_name].areas,
                with_arrows=granularity == "nom" or int(granularity) < 150,
                granularity=str(granularity),
            )


STARTS = {
    "de_ancient": de_ancient_spawns(),
    "de_anubis": de_anubis_spawns(),
    "de_dust2": de_dust2_spawns(),
    "de_inferno": de_inferno_spawns(),
    "de_mirage": de_mirage_spawns(),
    "de_nuke": de_nuke_spawns(),
    "de_overpass": de_overpass_spawns(),
    "de_train": de_train_spawns(),
    # "de_vertigo": de_vertigo_spawns(),
}

ENDS = {
    "de_ancient": de_ancient_meetings(),
    "de_anubis": de_anubis_meetings(),
    "de_dust2": de_dust2_meetings(),
    "de_inferno": de_inferno_meetings(),
    "de_mirage": de_mirage_meetings(),
    "de_nuke": de_nuke_meetings(),
    "de_overpass": de_overpass_meetings(),
    "de_train": de_train_meetings(),
    # "de_vertigo": de_vertigo_meetings(),
}


def plot_paths() -> None:
    print("Plotting paths.", flush=True)
    distances_data_path = Path("awpy/data/distances.pkl")

    if distances_data_path.is_file():
        with distances_data_path.open("rb") as f:
            distances = pickle.load(f)  # noqa: S301
    else:
        distances: dict[str, MapDistances] = {}
        for map_name in SUPPORTED_MAPS:
            distances[map_name] = {}
            print(f"At map: {map_name}")
            for start, end in itertools.product(STARTS[map_name], ENDS[map_name]):
                distances[map_name][PathPoints(start, end)] = {}
                for granularity in GRANULARITIES:
                    print(f"Grid {granularity}:")
                    target_dir = Path(f"awpy/data/nav_{granularity}")
                    target_dir.mkdir(exist_ok=True, parents=True)

                    nav = Nav.from_json(target_dir / f"{map_name}.json")
                    direct, rev = plot_path(
                        map_name,
                        nav,
                        start,
                        end,
                        "paths",
                        granularity=str(granularity),
                    )
                    distances[map_name][PathPoints(start, end)][str(granularity)] = PathDistances(direct, rev)

        with distances_data_path.open("wb") as f:
            pickle.dump(distances, f)

    # for map_name, map_distances in distances.items():
    #     for path_points, granularity_distances in map_distances.items():
    #         check_straight_and_reversed_distance(granularity_distances["nom"], map_name, path_points, "nom")
    #         check_straight_and_reversed_distance(granularity_distances["100"], map_name, path_points, "100")
    #         check_straight_and_reversed_distance(granularity_distances["200"], map_name, path_points, "200")

    #         check_100_200_distances(
    #             granularity_distances["100"],
    #             granularity_distances["200"],
    #             map_name,
    #             path_points,
    #         )


def _plot_areas_reachable_from(
    areas: Iterable[NavArea], map_name: str, nav: Nav, vis_checker: VisibilityChecker, granularity: str = "100"
) -> None:
    print(f"Plotting selected areas {map_name=} {granularity=}.", flush=True)
    for area in areas:
        reachable_areas: dict[str, list[NavArea]] = {
            "visibility": [],
            "reachability": [],
            "jumpability": [],
            "connectivity": [],
        }
        for other in nav.areas.values():
            if other.area_id == area.area_id:
                continue
            area_visible = areas_walkable(area, other, vis_checker)
            area_jumpable = area.centroid.can_jump_to(other.centroid)
            if area_visible:
                reachable_areas["visibility"].append(other)
            if area_jumpable:
                reachable_areas["jumpability"].append(other)
            if area_visible and area_jumpable:
                reachable_areas["reachability"].append(other)
            if other.area_id in area.connections:
                reachable_areas["connectivity"].append(other)

        for mode in ["visibility", "reachability", "jumpability", "connectivity"]:
            # print(f"Plotting selected area {area.area_id}: {map_name=} {granularity=} {mode=}.", flush=True)
            output_dir = Path(mode) / map_name / granularity
            output_dir.mkdir(exist_ok=True, parents=True)
            try:
                fig, axis = plot_map(map_name)
            except FileNotFoundError:
                return
            fig.set_size_inches(19.2, 21.6)
            _plot_tiles(nav.areas, map_name, axis)
            _plot_tiles({area.area_id: area}, map_name, axis, color="green")
            _plot_tiles({other.area_id: other for other in reachable_areas[mode]}, map_name, axis, color="red")
            for other in reachable_areas[mode]:
                _plot_connection(area, other, map_name, axis, with_arrows=False, color="red")
            plt.savefig(
                output_dir / f"{mode}_{map_name}_{granularity}_{area.area_id}.png",
                bbox_inches="tight",
                dpi=300,
            )
            fig.clear()
            plt.close(fig)


def plot_map_reachability_examples() -> None:
    for map_name in SUPPORTED_MAPS:
        vis_checker = load_vis_checker(map_name, suffix="-clippings")
        for granularity in GRANULARITIES:
            nav = Nav.from_json(f"awpy/data/nav_{granularity}/{map_name}.json")
            total_areas = len(nav.areas)
            n_points = 13
            _plot_areas_reachable_from(
                {
                    (nav.find_area(pos) or nav.find_closest_area_centroid(pos))
                    for pos in STARTS[map_name] + ENDS[map_name]
                }
                | (
                    set()
                    if granularity == "nom"
                    else {nav.areas[idx] for idx in (range(0, total_areas, round(total_areas / n_points)))}
                ),
                map_name,
                nav,
                vis_checker,
                granularity=granularity,
            )


# plot_triangles(with_clipping=True)
# generate_grids()
# plot_paths()
# plot_map_reachability_examples()
# for map_name in SUPPORTED_MAPS:
#     for style in ("fine", "rough"):
#         for granularity in GRANULARITIES:
#             plot_spread(map_name, granularity, style)
#               generate_spread_gif(map_name, granularity, style)

plot_spread_from_input("de_ancient", "200", "fine", Nav.from_json("awpy/data/nav_200/de_ancient.json"))
plot_spread_from_input("de_ancient", "200", "rough", Nav.from_json("awpy/data/nav_200/de_ancient.json"))
