"""Stuff."""

import importlib.resources
import itertools
import logging
import math
import os
import pickle
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.axes import Axes
from matplotlib.collections import PatchCollection
from shapely import Point, Polygon
from tqdm import tqdm

from awpy.constants import JUMP_HEIGHT, PLAYER_EYE_LEVEL
from awpy.data.map_data import MAP_DATA
from awpy.nav import NAV_DATA, Nav, NavArea, PathResult
from awpy.plot.utils import game_to_pixel
from awpy.spawn import SPAWNS_DATA, Spawns
from awpy.vector import Vector3
from awpy.visibility import VIS_CHECKERS, BVHNode

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
GRANULARITIES = (100, 200)


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
) -> None:
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


def _plot_points(points: list[Vector3], map_name: str, axis: Axes) -> None:
    for point in points:
        x, y, _ = game_to_pixel(map_name, point)
        axis.plot(
            x,
            y,
            marker="o",
            color="green",
            markersize=5,
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
    # networkX type hints suck. So pyright does not know that we only
    # get a two sized tuple for our case.
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


@dataclass
class NewNavArea:
    corners: list[Vector3]
    orig_ids: set[int]
    connections: set[int] = field(default_factory=set)

    def polygon(self) -> Polygon:
        return Polygon([(c.x, c.y) for c in self.corners])

    def distance(self, other: "NewNavArea") -> float:
        return self.polygon().centroid.distance(other.polygon().centroid)


def regularize_nav_areas(  # noqa: PLR0912, PLR0915
    nav_areas: dict[int, NavArea],
    grid_granularity: int,
    map_name: str,
) -> dict[int, NavArea]:
    # Collect all x,y coordinates over all nav areas
    xs: list[float] = []
    ys: list[float] = []
    area_polygons: dict[int, Polygon] = {}
    area_levels: dict[int, float] = {}

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
                new_cells.append(NewNavArea(corners=corners, orig_ids=cell_orig_ids))

    new_nav_areas: dict[int, NewNavArea] = {}
    old_to_new_children: dict[int, set[int]] = defaultdict(set)
    for idx, new_cell in enumerate(new_cells):
        new_nav_areas[idx] = new_cell
        for orig_id in new_cell.orig_ids:
            old_to_new_children[orig_id].add(idx)

    for area1 in nav_areas.values():
        for area2 in nav_areas.values():
            if area1 == area2 or area2.area_id in area1.connections:
                continue
            if (
                (set(area1.ladders_above) & set(area2.ladders_below))
                or (set(area1.ladders_below) & set(area2.ladders_above))
                or (area1.centroid.can_jump_to(area2.centroid) and areas_visible(area1, area2, map_name))
            ):
                area1.connections.append(area2.area_id)

    # Build connectivity based solely on the new cell's orig_ids.
    # For a new cell A with orig set A_orig, connect to new cell B with orig set B_orig if:
    # ∃ a in A_orig and b in B_orig with a == b or b in nav_areas[a].connections
    for idx_a, new_area in tqdm(new_nav_areas.items(), desc="Connections"):
        parent_areas = new_area.orig_ids
        for parent_area in parent_areas:
            siblings = old_to_new_children[parent_area]
            new_area.connections.update(sibling for sibling in siblings if sibling != idx_a)

    for a_idx, area_a in nav_areas.items():
        children_of_a = old_to_new_children[a_idx]
        for neighbor_of_a_idx in area_a.connections:
            children_of_neighbor_of_a = old_to_new_children[neighbor_of_a_idx]

            neighbors_of_children_of_a: set[int] = set(children_of_a)
            for child_of_a in children_of_a:
                neighbors_of_children_of_a.update(new_nav_areas[child_of_a].connections)

            if not children_of_neighbor_of_a & neighbors_of_children_of_a:
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
                )[:5]
                for closest_children in closest_childrens:
                    new_nav_areas[closest_children[0]].connections.add(closest_children[1])

    return {
        idx: NavArea(area_id=idx, corners=area.corners, connections=list(area.connections))
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
) -> tuple[float, float]:
    output_dir = Path(output_dir) / map_name / granularity
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    try:
        fig, axis = plot_map(map_name)
    except FileNotFoundError:
        return float("inf"), float("inf")
    fig.set_size_inches(19.2, 21.6)
    start_area = map_nav.find_area(start)
    end_area = map_nav.find_area(end)

    if not start_area or not end_area:
        print(f"Didnt find start {start_area}-{start} or end area {end_area}-{end}")
        return float("inf"), float("inf")

    _plot_tiles({0: start_area}, map_name, axis, color="green")
    _plot_tiles({1: end_area}, map_name, axis, color="red")
    _plot_points([start, end], map_name, axis)
    shortest_path, direct_distance = map_nav.find_path(start_area.area_id, end_area.area_id, weight="dist")
    shortest_path_reversed, reversed_distance = map_nav.find_path(end_area.area_id, start_area.area_id, weight="dist")
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
        print(f"At map: {map_name} for path: {path_points} the between 100 and 200 granularity are not close.")

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
    return [a_site, mid, water, b_site, tarp]


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
    return [ct_spawn, t_spawn]


def de_inferno_meetings() -> list[Vector3]:
    b_site = Vector3(40, 2837, 225)
    mid = Vector3(476, 585, 148)
    second = Vector3(595, -94, 136)
    apps = Vector3(1434, -286, 320)
    return [b_site, mid, second, apps]


def de_mirage_spawns() -> list[Vector3]:
    ct_spawn = Vector3(-1776, -1800, -203)
    t_spawn = Vector3(1278, -350, -104)
    return [ct_spawn, t_spawn]


def de_mirage_meetings() -> list[Vector3]:
    apps = Vector3(-1462, 734, 16)
    short = Vector3(-822, -14, -105)
    mid = Vector3(91, -682, -112)
    conn = Vector3(-663, -1152, -104)
    ramp = Vector3(335, -1565, -121)
    palace = Vector3(443, -2292, 24)
    return [apps, short, mid, conn, ramp, palace]


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
    return [ct_spawn, t_spawn]


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
    return [ct_spawn, t_spawn]


def de_train_meetings() -> list[Vector3]:
    ivy = Vector3(1034, 1497, -152)
    a_site = Vector3(391, 109, -152)
    pop = Vector3(-901, -308, -149)
    b_halls = Vector3(-987, -1004, -90)
    return [ivy, a_site, pop, b_halls]


@dataclass
class SpawnDistance:
    area: NavArea
    distance: float
    path: list[int] = field(default_factory=list)


@dataclass
class SpawnDistances:
    CT: list[SpawnDistance]
    T: list[SpawnDistance]


def get_distances_from_spawns(map_areas: Nav, spawns: Spawns) -> SpawnDistances:
    ct_distances: list[SpawnDistance] = []
    t_distances: list[SpawnDistance] = []
    for area in tqdm(map_areas.areas.values()):
        ct_path = min(
            (map_areas.find_path(spawn_point, area.area_id, weight="dist") for spawn_point in spawns.CT),
            default=PathResult(distance=float("inf"), path=[]),
            key=lambda path_result: path_result.distance,
        )
        t_path = min(
            (map_areas.find_path(spawn_point, area.area_id, weight="dist") for spawn_point in spawns.T),
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


def areas_visible(area1: NavArea, area2: NavArea, map_name: str) -> bool:
    used_centroid1 = Vector3(area1.centroid.x, area1.centroid.y, area1.centroid.z + PLAYER_EYE_LEVEL)
    used_centroid2 = Vector3(area2.centroid.x, area2.centroid.y, area2.centroid.z + PLAYER_EYE_LEVEL)
    return VIS_CHECKERS[map_name].is_visible(used_centroid1, used_centroid2)


def establish_visibilities(
    current_area: SpawnDistance,
    previous_opposing_areas: list[SpawnDistance],
    map_name: str,
    *,
    own_spotted_areas: set[int],
    opposing_spotted_areas: set[int],
) -> list[SpawnDistance]:
    result: list[SpawnDistance] = []
    for opposing_area in sorted(previous_opposing_areas, key=lambda area: area.distance, reverse=True):
        # Skip this if both areas come from ones that have already been spotted.
        if any(path_id in own_spotted_areas for path_id in current_area.path) and any(
            path_id in opposing_spotted_areas for path_id in opposing_area.path
        ):
            continue
        if areas_visible(current_area.area, opposing_area.area, map_name):
            own_spotted_areas.add(current_area.area.area_id)
            opposing_spotted_areas.add(opposing_area.area.area_id)
            result.append(opposing_area)
    return result


def round_up_to_next_100(n: float) -> int:
    return math.ceil(n / 100) * 100


def _plot_visibility_connection(
    area1: SpawnDistance,
    area2: SpawnDistance,
    map_nav: Nav,
    map_name: str,
    axis: Axes,
    color: str = "red",
    lw: float = 1.0,
) -> None:
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


def _plot_collision_triangles(map_name: str, axis: Axes) -> None:
    vis_checker = VIS_CHECKERS[map_name]
    _plot_node(vis_checker.root, axis, map_name)


def plot_triangles() -> None:
    print("Plotting triangles.", flush=True)
    for map_name in VIS_CHECKERS:
        print(f"Plotting triangles for {map_name}.", flush=True)
        output_dir = Path("triangles")
        output_dir.mkdir(exist_ok=True, parents=True)

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

        _plot_collision_triangles(map_name, axis)

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
            output_dir / f"triangles_{map_name}.png",
            bbox_inches="tight",
            dpi=300,
        )
        fig.clear()
        plt.close(fig)


def plot_spread() -> None:  # noqa: PLR0915
    print("Plotting spreads.", flush=True)
    map_name = "de_dust2"
    d2_nav = NAV_DATA[map_name]
    d2_spawns = SPAWNS_DATA[map_name]
    d2_spawn_distances_path = Path("awpy/data/spawn_distances.pkl")

    if d2_spawn_distances_path.is_file():
        with d2_spawn_distances_path.open("rb") as f:
            d2_spawn_distances: SpawnDistances = pickle.load(f)  # noqa: S301
    else:
        d2_spawn_distances = get_distances_from_spawns(d2_nav, d2_spawns)
        with d2_spawn_distances_path.open("wb") as f:
            pickle.dump(d2_spawn_distances, f)

    ct_index = 0
    marked_areas_ct: set[int] = set()
    marked_areas_t: set[int] = set()
    new_marked_areas_ct: set[int] = set()
    new_marked_areas_t: set[int] = set()
    t_index = 0
    output_dir = Path("spread") / map_name
    output_dir.mkdir(exist_ok=True, parents=True)

    last_plotted = float("-inf")

    visibility_connections: list[tuple[SpawnDistance, SpawnDistance]] = []
    spotted_areas_t: set[int] = set()
    spotted_areas_ct: set[int] = set()

    while True:
        if (current_ct_area := d2_spawn_distances.CT[ct_index]).distance < (
            current_t_area := d2_spawn_distances.T[t_index]
        ).distance:
            current_area = current_ct_area
            new_marked_areas_ct.add(current_ct_area.area.area_id)
            opposing_spotted_areas = spotted_areas_t
            own_spotted_areas = spotted_areas_ct
            opposing_previous_areas = [
                area for area in d2_spawn_distances.T if area.area.area_id in (marked_areas_t | new_marked_areas_t)
            ]
            ct_index += 1
        else:
            current_area = current_t_area
            new_marked_areas_t.add(current_t_area.area.area_id)
            opposing_spotted_areas = spotted_areas_ct
            own_spotted_areas = spotted_areas_t
            opposing_previous_areas = [
                area for area in d2_spawn_distances.CT if area.area.area_id in (marked_areas_ct | new_marked_areas_ct)
            ]
            t_index += 1

        if current_area.distance == float("inf"):
            print(ct_index, t_index, current_area.distance)
            break

        visible_areas = establish_visibilities(
            current_area,
            opposing_previous_areas,
            map_name=map_name,
            own_spotted_areas=own_spotted_areas,
            opposing_spotted_areas=opposing_spotted_areas,
        )

        for spotted_by_area in visible_areas:
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
            {area_id: d2_nav.areas[area_id] for area_id in (marked_areas_ct | marked_areas_t)},
            map_name=map_name,
            axis=axis,
            color="olive",
        )
        _plot_tiles(
            {area_id: d2_nav.areas[area_id] for area_id in (new_marked_areas_ct | new_marked_areas_t)},
            map_name=map_name,
            axis=axis,
            color="green",
        )

        _plot_tiles(
            {
                area_id: d2_nav.areas[area_id]
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
                for area_id, area in d2_nav.areas.items()
                if area_id not in marked_areas_ct and area_id not in marked_areas_t
            },
            map_name=map_name,
            axis=axis,
            color="yellow",
        )

        for area1, area2 in visibility_connections:
            _plot_visibility_connection(area1, area2, d2_nav, map_name, axis, color="red", lw=1.0)

        plt.savefig(
            output_dir / f"spread_{map_name}_{current_area.distance}.png",
            bbox_inches="tight",
            dpi=300,
        )
        fig.clear()
        plt.close(fig)


def generate_grids() -> None:
    print("Generating grids.", flush=True)
    print("Nom:")
    for map_name in NAV_DATA:
        if map_name not in SUPPORTED_MAPS:
            continue
        print(f"At map: {map_name}")
        map_areas = NAV_DATA[map_name].areas
        plot_map_connections(
            "connections",
            map_areas,
            map_name=map_name,
            with_arrows=True,
            granularity="nom",
        )

    for granularity in GRANULARITIES:
        print(f"Grid {granularity}:")
        target_dir = Path(f"awpy/data/nav_{granularity}")
        target_dir.mkdir(exist_ok=True, parents=True)

        for map_name in NAV_DATA:
            if map_name not in SUPPORTED_MAPS:
                continue
            print(f"At map: {map_name}")

            target_path = target_dir / f"{map_name}.json"
            if target_path.is_file():
                modified_nav = Nav.from_json(target_path)
            else:
                map_areas = regularize_nav_areas(
                    NAV_DATA[map_name].areas, grid_granularity=granularity, map_name=map_name
                )
                modified_nav = Nav(areas=map_areas)
                modified_nav.to_json(target_path)

            plot_map_connections(
                "connections",
                modified_nav.areas,
                map_name=map_name,
                extra_areas=NAV_DATA[map_name].areas,
                with_arrows=granularity < 150,
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
        for map_name in STARTS.keys() & ENDS.keys():
            distances[map_name] = {}
            print(f"At map: {map_name}")
            for start, end in itertools.product(STARTS[map_name], ENDS[map_name]):
                distances[map_name][PathPoints(start, end)] = {}
                print("Nom:")
                direct, rev = plot_path(
                    map_name,
                    NAV_DATA[map_name],
                    start,
                    end,
                    "paths",
                    granularity="nom",
                )
                distances[map_name][PathPoints(start, end)]["nom"] = PathDistances(direct, rev)

                for granularity in GRANULARITIES:
                    distances[map_name][PathPoints(start, end)][str(granularity)] = PathDistances(direct, rev)
                    print(f"Grid {granularity}:")
                    target_dir = Path(f"awpy/data/nav_{granularity}")
                    target_dir.mkdir(exist_ok=True, parents=True)

                    nav = Nav.from_json(target_dir / f"{map_name}.json")

                    plot_path(
                        map_name,
                        nav,
                        start,
                        end,
                        "paths",
                        granularity=str(granularity),
                    )
        with distances_data_path.open("wb") as f:
            pickle.dump(distances, f)

    for map_name, map_distances in distances.items():
        for path_points, granularity_distances in map_distances.items():
            # check_straight_and_reversed_distance(
            #     granularity_distances["nom"], map_name, path_points, "nom"
            # )
            # check_straight_and_reversed_distance(
            #     granularity_distances["100"], map_name, path_points, "100"
            # )
            # check_straight_and_reversed_distance(
            #     granularity_distances["200"], map_name, path_points, "200"
            # )

            check_100_200_distances(
                granularity_distances["100"],
                granularity_distances["200"],
                map_name,
                path_points,
            )


# plot_triangles()
plot_spread()
# generate_grids()
# plot_paths()
