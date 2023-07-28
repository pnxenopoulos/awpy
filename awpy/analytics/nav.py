"""Functions for finding distances between points, areas or states.

Example::

    from awpy.analytics.nav import area_distance

    geodesic_dist = area_distance(
        map_name="de_dust2", area_a=152, area_b=8970, dist_type="geodesic"
    )
    f, ax = plot_map(map_name="de_dust2", map_type="simpleradar", dark=True)

    for a in NAV["de_dust2"]:
        area = NAV["de_dust2"][a]
        color = "None"
        if a in geodesic_dist["areas"]:
            color = "red"
        width = area["southEastX"] - area["northWestX"]
        height = area["northWestY"] - area["southEastY"]
        southwest_x = area["northWestX"]
        southwest_y = area["southEastY"]
        rect = patches.Rectangle(
            (southwest_x, southwest_y),
            width,
            height,
            linewidth=1,
            edgecolor="yellow",
            facecolor=color,
        )
        ax.add_patch(rect)

https://github.com/pnxenopoulos/awpy/blob/main/examples/03_Working_with_Navigation_Meshes.ipynb
"""
import itertools
import json
import logging
import math
import os
import sys
from collections import defaultdict
from itertools import pairwise
from statistics import mean, median
from typing import Literal, get_args

import networkx as nx
import numpy as np
import numpy.typing as npt
from scipy.spatial import distance
from shapely.geometry import Polygon
from sympy.utilities.iterables import multiset_permutations

from awpy.data import AREA_DIST_MATRIX, NAV, NAV_GRAPHS, PATH, PLACE_DIST_MATRIX
from awpy.types import (
    AreaMatrix,
    ClosestArea,
    DistanceObject,
    DistanceType,
    GameFrame,
    PlaceMatrix,
    TileId,
    Token,
)


def point_in_area(map_name: str, area_id: int, point: list[float]) -> bool:
    """Returns if the point is within a nav area for a map.

    Args:
        map_name (string): Map to consider
        area_id (int): Area ID as an integer
        point (list): Point as a list [x,y,z]

    Returns:
        True if area contains the point, false if not

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If area_id is not in awpy.data.NAV[map_name]
                    If the length of point is not 3
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if area_id not in NAV[map_name]:
        msg = "Area ID not found."
        raise ValueError(msg)
    # Three dimensional space. Unlikely to change anytime soon
    if len(point) != 3:  # noqa: PLR2004
        msg = "Point must be a list [X,Y,Z]"
        raise ValueError(msg)
    contains_x = (
        min(NAV[map_name][area_id]["northWestX"], NAV[map_name][area_id]["southEastX"])
        < point[0]
        < max(
            NAV[map_name][area_id]["northWestX"], NAV[map_name][area_id]["southEastX"]
        )
    )
    contains_y = (
        min(NAV[map_name][area_id]["northWestY"], NAV[map_name][area_id]["southEastY"])
        < point[1]
        < max(
            NAV[map_name][area_id]["northWestY"], NAV[map_name][area_id]["southEastY"]
        )
    )
    return contains_x and contains_y


def find_closest_area(
    map_name: str, point: list[float], *, flat: bool = False
) -> ClosestArea:
    """Finds the closest area in the nav mesh.

    Searches through all the areas by comparing point to area centerpoint.

    Args:
        map_name (string): Map to search
        point (list): Point as a list [x,y,z]
        flat (Boolean): Whether z should be ignored.

    Returns:
        A dict containing info on the closest area

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If the length of point is not 3
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if flat:
        if len(point) != 2:  # noqa: PLR2004
            msg = "Point must be a list [X,Y] when flat is True"
            raise ValueError(msg)
    elif len(point) != 3:  # noqa: PLR2004
        msg = "Point must be a list [X,Y,Z]"
        raise ValueError(msg)
    closest_area: ClosestArea = {
        "mapName": map_name,
        # I do not think there is anyway this can actually be None
        # And not allowing it to be None makes things easier with type checking
        "areaId": 0,
        "distance": float("inf"),
    }
    for area in NAV[map_name]:
        avg_x, avg_y, avg_z = _get_area_center(map_name, area)
        if flat:
            dist = np.sqrt((point[0] - avg_x) ** 2 + (point[1] - avg_y) ** 2)
        else:
            dist = np.sqrt(
                (point[0] - avg_x) ** 2
                + (point[1] - avg_y) ** 2
                + (point[2] - avg_z) ** 2
            )
        if dist < closest_area["distance"]:
            closest_area["areaId"] = area
            closest_area["distance"] = dist
    return closest_area


def _check_arguments_area_distance(
    map_name: str,
    area_a: int,
    area_b: int,
    dist_type: DistanceType = "graph",
) -> None:
    """Returns the distance between two areas.

    Dist type can be [graph, geodesic, euclidean].

    Args:
        map_name (string): Map to consider
        area_a (int): Area id
        area_b (int): Area id
        dist_type (string, optional): String indicating the type of distance to use
            (graph, geodesic or euclidean). Defaults to 'graph'

    Returns:
        A dict containing info on the path between two areas.

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If either area_a or area_b is not in awpy.data.NAV[map_name]
                    If the dist_type is not one of ["graph", "geodesic", "euclidean"]
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if (area_a not in NAV[map_name].keys()) or (area_b not in NAV[map_name].keys()):
        msg = "Area ID not found."
        raise ValueError(msg)
    if dist_type not in get_args(DistanceType):
        msg = "dist_type can only be graph, geodesic or euclidean"
        raise ValueError(msg)


def _get_area_center(map_name: str, area: int) -> tuple[float, float, float]:
    """Get the coordinates of the center of an area.

    Args:
        map_name (string): Map to consider
        area (int): Area id

    Returns:
        Tuple of x, y, z coordinates of the area center.
    """
    area_x = (NAV[map_name][area]["southEastX"] + NAV[map_name][area]["northWestX"]) / 2
    area_y = (NAV[map_name][area]["southEastY"] + NAV[map_name][area]["northWestY"]) / 2
    area_z = (NAV[map_name][area]["southEastZ"] + NAV[map_name][area]["northWestZ"]) / 2
    return area_x, area_y, area_z


def _get_euclidean_area_distance(
    map_name: str,
    area_a: int,
    area_b: int,
) -> float:
    """Returns the euclidean distance the centers of two areas.

    Args:
        map_name (string): Map to search
        area_a (int): Area id
        area_b (int): Area id

    Returns:
        Distance between the centers of the two areas.
    """
    area_a_x, area_a_y, area_a_z = _get_area_center(map_name, area_a)
    area_b_x, area_b_y, area_b_z = _get_area_center(map_name, area_b)
    return math.sqrt(
        (area_a_x - area_b_x) ** 2
        + (area_a_y - area_b_y) ** 2
        + (area_a_z - area_b_z) ** 2
    )


def _get_graph_area_distance(
    map_graph: nx.DiGraph,
    area_a: int,
    area_b: int,
) -> tuple[float, list[int]]:
    """Returns the graph distance between two areas.

    Args:
        map_graph (nx.DiGraph): DiGraph for the considered map
        area_a (int): Area id
        area_b (int): Area id

    Returns:
        tuple containing
        - Distance between two areas as length of the path
        - Path between the two areas as list of (int) nodes
    """
    try:
        discovered_path = nx.bidirectional_shortest_path(map_graph, area_a, area_b)
    except nx.NetworkXNoPath:
        return float("inf"), []
    return len(discovered_path) - 1, discovered_path


def _get_geodesic_area_distance(
    map_graph: nx.DiGraph,
    area_a: int,
    area_b: int,
) -> tuple[float, list[int]]:
    """Returns the geodesic distance between two areas.

    Args:
        map_graph (nx.DiGraph): DiGraph for the considered map
        area_a (int): Area id
        area_b (int): Area id

    Returns:
        tuple containing
        - Distance between two areas as geodesic cost
        - Path between the two areas as list of (int) nodes
    """

    def dist_heuristic(node_a: int, node_b: int) -> float:
        return distance.euclidean(
            map_graph.nodes[node_a]["center"], map_graph.nodes[node_b]["center"]
        )

    try:
        geodesic_path = nx.astar_path(
            map_graph, area_a, area_b, heuristic=dist_heuristic, weight="weight"
        )
        geodesic_cost = sum(
            map_graph[u][v]["weight"] for u, v in pairwise(geodesic_path)
        )
    except nx.NetworkXNoPath:
        return float("inf"), []
    return geodesic_cost, geodesic_path


def area_distance(
    map_name: str,
    area_a: int,
    area_b: int,
    dist_type: DistanceType = "graph",
) -> DistanceObject:
    """Returns the distance between two areas.

    Dist type can be [graph, geodesic, euclidean].

    Args:
        map_name (string): Map to consider
        area_a (int): Area id
        area_b (int): Area id
        dist_type (string, optional): String indicating the type of distance to use
            (graph, geodesic or euclidean). Defaults to 'graph'

    Returns:
        A dict containing info on the path between two areas.

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If either area_a or area_b is not in awpy.data.NAV[map_name]
                    If the dist_type is not one of ["graph", "geodesic", "euclidean"]
    """
    _check_arguments_area_distance(map_name, area_a, area_b, dist_type)
    map_graph = NAV_GRAPHS[map_name]
    distance_obj: DistanceObject = {
        "distanceType": dist_type,
        "distance": float("inf"),
        "areas": [],
    }
    if dist_type == "graph":
        distance_obj["distance"], distance_obj["areas"] = _get_graph_area_distance(
            map_graph, area_a, area_b
        )
        return distance_obj
    if dist_type == "geodesic":
        distance_obj["distance"], distance_obj["areas"] = _get_geodesic_area_distance(
            map_graph, area_a, area_b
        )
        return distance_obj
    distance_obj["distance"] = _get_euclidean_area_distance(map_name, area_a, area_b)
    return distance_obj


PointDistanceType = Literal[DistanceType, "manhattan", "canberra", "cosine"]


def point_distance(
    map_name: str,
    point_a: list[float],
    point_b: list[float],
    dist_type: PointDistanceType = "graph",
) -> DistanceObject:
    """Returns the distance between two points.

    Args:
        map_name (string): Map to consider
        point_a (list): Point as a list (x,y,z)
        point_b (list): Point as a list (x,y,z)
        dist_type (string, optional): String indicating the type of distance to use.
            Can be graph, geodesic, euclidean, manhattan, canberra or cosine.
            Defaults to 'graph'

    Returns:
        A dict containing info on the distance between two points.

    Raises:
        ValueError: If map_name is not in awpy.data.NAV:
                        if dist_type is "graph" or "geodesic"
                    If either point_a or point_b does not have a length of 3
                        (for "graph" or "geodesic" dist_type)
    """
    if dist_type not in get_args(PointDistanceType):
        msg = (
            "dist_type can only be graph, geodesic, "
            "euclidean, manhattan, canberra or cosine"
        )
        raise ValueError(msg)
    if dist_type in {"graph", "geodesic"}:
        if map_name not in NAV:
            msg = "Map not found."
            raise ValueError(msg)
        # Three dimensional space. Unlikely to change anytime soon
        if len(point_a) != 3 or len(point_b) != 3:  # noqa: PLR2004
            msg = "When using graph or geodesic distance, point must be X/Y/Z"
            raise ValueError(msg)
    distance_obj: DistanceObject = {
        "distanceType": dist_type,
        "distance": float("inf"),
        "areas": [],
    }
    if dist_type in ("graph", "geodesic"):
        area_a = find_closest_area(map_name, point_a)["areaId"]
        area_b = find_closest_area(map_name, point_b)["areaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    if dist_type == "euclidean":
        distance_obj["distance"] = distance.euclidean(point_a, point_b)
        return distance_obj
    if dist_type == "manhattan":
        distance_obj["distance"] = distance.cityblock(point_a, point_b)
        return distance_obj
    if dist_type == "canberra":
        distance_obj["distance"] = float(distance.canberra(point_a, point_b))
        return distance_obj
    # redundant due to asserting that only ["graph", "geodesic", "euclidean", manhattan,
    # canberra, cosine] are valid and if checks that it is neither none of the others
    # if dist_type == "cosine":
    distance_obj["distance"] = float(distance.cosine(point_a, point_b))
    return distance_obj


def generate_position_token(map_name: str, frame: GameFrame) -> Token:
    """Generates the position token for a game frame.

    Args:
        map_name (string): Map to consider
        frame (dict): A game frame

    Returns:
        A dict containing the T token, CT token and combined token (T + CT concatenated)

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If either side ("ct" or "t") in the frame has no players
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    ct_players = frame["ct"]["players"]
    t_players = frame["t"]["players"]
    if (
        ct_players is None
        or t_players is None
        or len(ct_players) == 0
        or len(t_players) == 0
    ):
        msg = "CT or T players has length of 0"
        raise ValueError(msg)
    # Create map area list
    map_area_names = sorted(
        {NAV[map_name][area_id]["areaName"] for area_id in NAV[map_name]}
    )
    # Create token
    ct_token = np.zeros(len(map_area_names), dtype=np.int8)
    # We know this is not None because otherwise we would have already
    # thrown a ValueError
    for player in ct_players:
        if player["isAlive"]:
            closest_area = find_closest_area(
                map_name, [player["x"], player["y"], player["z"]]
            )
            ct_token[
                map_area_names.index(NAV[map_name][closest_area["areaId"]]["areaName"])
            ] += 1
    t_token = np.zeros(len(map_area_names), dtype=np.int8)
    # Same here
    for player in t_players:
        if player["isAlive"]:
            closest_area = find_closest_area(
                map_name, [player["x"], player["y"], player["z"]]
            )
            t_token[
                map_area_names.index(NAV[map_name][closest_area["areaId"]]["areaName"])
            ] += 1
    # Create payload
    ttoken = (
        str(t_token).replace("'", "").replace("[", "").replace("]", "").replace(" ", "")
    )
    cttoken = (
        str(ct_token)
        .replace("'", "")
        .replace("[", "")
        .replace("]", "")
        .replace(" ", "")
    )
    token: Token = {"tToken": ttoken, "ctToken": cttoken, "token": cttoken + ttoken}
    return token


def tree() -> dict:
    """Builds tree data structure from nested defaultdicts.

    Args:
        None

    Returns:
        An empty tree
    """

    def the_tree() -> dict:
        return defaultdict(the_tree)

    return the_tree()


def _save_matrix_to_file(
    map_name: str,
    dist_matrix: AreaMatrix | PlaceMatrix,
    matrix_type: Literal["area", "place"],
) -> None:
    """Save the given matrix to a json file.

    Args:
        map_name (str): Name of the map corresponding to the matrix
        dist_matrix (AreaMatrix | PlaceMatrix): The nested dict to save to file.
        matrix_type (Literal["area", "place"]): Whether an area or place matrix
            is being saved
    """
    if matrix_type not in ("area", "place"):
        msg = f"Matrix type has to be one of ('area', 'place') but was {matrix_type}!"
        raise ValueError(msg)
    with open(
        os.path.join(PATH, "nav", f"{matrix_type}_distance_matrix_{map_name}.json"),
        "w",
        encoding="utf8",
    ) as json_file:
        json.dump(dist_matrix, json_file)


def generate_area_distance_matrix(map_name: str, *, save: bool = False) -> AreaMatrix:
    """Generates or grabs a tree like nested dictionary containing distance matrices.

    Structures is [map_name][area1id][area2id][dist_type(euclidean,graph,geodesic)]

    Note that this can take 20min to 13h to run depending on the map and produces
    an output file of 50-600mb. If you run this offline and want to store the result for
    later reuse make sure to set 'save=True'!

    Args:
        map_name (string): Map to generate the place matrix for
        save (bool, optional): Whether to save the matrix to file Defaults to 'False'

    Returns:
        Tree structure containing distances for all area pairs on all maps

    Raises:
        ValueError: Raises a ValueError if map_name is not in awpy.data.NAV
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.warning(
        "Note that this can take 20min to 13h to run depending on the"
        " map and produces an output file of 50-600mb.\n"
        "If you run this offline and want to store the result "
        "for later reuse make sure to set 'save=True'!"
    )
    # Initialize the dict structure
    area_distance_matrix: AreaMatrix = tree()
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    # And there over each area
    for area1 in NAV[map_name]:
        logging.info("Calculating distances from area %s", area1)
        # Precompute the tile center
        area1_x, area1_y, area1_z = _get_area_center(map_name, area1)
        # Loop over every pair of areas
        for area2 in NAV[map_name]:
            # Compute center of second area
            area2_x, area2_y, area2_z = _get_area_center(map_name, area2)
            # Calculate basic euclidean distance
            area_distance_matrix[str(area1)][str(area2)]["euclidean"] = math.sqrt(
                (area1_x - area2_x) ** 2
                + (area1_y - area2_y) ** 2
                + (area1_z - area2_z) ** 2
            )
            # Also get graph distance
            area_distance_matrix[str(area1)][str(area2)]["graph"] = area_distance(
                map_name, area1, area2, dist_type="graph"
            )["distance"]
            # And geodesic like distance
            area_distance_matrix[str(area1)][str(area2)]["geodesic"] = area_distance(
                map_name, area1, area2, dist_type="geodesic"
            )["distance"]
    if save:
        _save_matrix_to_file(map_name, area_distance_matrix, "area")
    return area_distance_matrix


def _check_place_matrix_map_name(map_name: str) -> None:
    """Checks if the given map_name is in NAV and AREA_DIST_MATRIX.

    Raises a ValueError if the map_name is not in NAV and
    logs a warning if it is not in AREA_DIST_MATRIX.

    Args:
        map_name (str): Name of the map to check

    Raises:
        ValueError: If the map is not in NAV.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if map_name not in AREA_DIST_MATRIX:
        logging.warning(
            """Skipping calculation of median distances between places.
If you want to have those included run `generate_area_distance_matrix` first!"""
        )


def _get_area_place_mapping(map_name: str) -> dict[str, list[int]]:
    """Get the mapping of a named place to all areas that it contains.

    Get the mapping "areaName": [areas that have this area name]

    Args:
        map_name (str): Name of the map to get the mapping for.

    Returns:
        The mapping "areaName": [areas that have this area name] for each "areaName"
    """
    area_mapping = defaultdict(list)
    # Get the mapping "areaName": [areas that have this area name]
    for area in NAV[map_name]:
        area_mapping[NAV[map_name][area]["areaName"]].append(area)
    return area_mapping


def _get_median_place_distance(
    map_name: str,
    place1: str,
    place2: str,
    area_mapping: dict[str, list[int]],
    dist_type: DistanceType,
) -> float:
    """Get the median distance between the areas of two places.

    Args:
        map_name (str): Name of the map to get the distances for
        place1 (str): First place in the pair
        place2 (str): Second place in the pair
        area_mapping (dict[str, list[int]]): Mapping of each place to all area it
            contains
        dist_type (DistanceType): Distance type to consider.

    Returns:
        Median distance between all areas in two places.
    """
    connections = []
    for sub_area1 in area_mapping[place1]:
        connections.extend(
            AREA_DIST_MATRIX[map_name][str(sub_area1)][str(sub_area2)][dist_type]
            for sub_area2 in area_mapping[place2]
        )
    return median(connections)


def generate_place_distance_matrix(map_name: str, *, save: bool = False) -> PlaceMatrix:
    """Generates or grabs a tree like nested dictionary containing distance matrices.

    Structures is:
    [map_name][placeid][place2id][dist_type(euclidean,graph,geodesic)]
    [reference_point(centroid,representative_point,median_dist)]

    Args:
        map_name (string): Map to generate the place matrix for
        save (bool, optional): Whether to save the matrix to file. Defaults to 'False'

    Returns:
        Tree structure containing distances for all place pairs on all maps

    Raises:
        ValueError: Raises a ValueError if map_name is not in awpy.data.NAV
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    _check_place_matrix_map_name(map_name)
    place_distance_matrix: PlaceMatrix = tree()
    area_mapping = _get_area_place_mapping(map_name)
    # Get the centroids and representative points for each named place on the map
    centroids, reps = generate_centroids(map_name)
    # Loop over all pairs of named places
    for place1, centroid1 in centroids.items():
        logging.info("Calculating distances from place %s", place1)
        for place2, centroid2 in centroids.items():
            # Loop over all three considered distance types
            for dist_type in ("geodesic", "graph", "euclidean"):
                # If precomputed values do not exist calculate them
                if map_name not in AREA_DIST_MATRIX:
                    # Distances between the centroids for each named place
                    place_distance_matrix[place1][place2][dist_type][
                        "centroid"
                    ] = area_distance(
                        map_name, centroid1, centroid2, dist_type=dist_type
                    )[
                        "distance"
                    ]
                    # Distances between the representative points for each named place
                    place_distance_matrix[place1][place2][dist_type][
                        "representative_point"
                    ] = area_distance(
                        map_name, reps[place1], reps[place2], dist_type=dist_type
                    )[
                        "distance"
                    ]
                    # Median of all the distance pairs for areaA in place1
                    # to areaB in place2
                    # Without having the AREA_DISTANCE_MATRIX precalculated
                    # this step could take up to 13 hours
                    place_distance_matrix[place1][place2][dist_type][
                        "median_dist"
                    ] = 0.0
                else:
                    place_distance_matrix[place1][place2][dist_type][
                        "centroid"
                    ] = AREA_DIST_MATRIX[map_name][str(centroid1)][str(centroid2)][
                        dist_type
                    ]
                    place_distance_matrix[place1][place2][dist_type][
                        "representative_point"
                    ] = AREA_DIST_MATRIX[map_name][str(reps[place1])][
                        str(reps[place2])
                    ][
                        dist_type
                    ]
                    place_distance_matrix[place1][place2][dist_type][
                        "median_dist"
                    ] = _get_median_place_distance(
                        map_name, place1, place2, area_mapping, dist_type
                    )
    if save:
        _save_matrix_to_file(map_name, place_distance_matrix, "place")
    return place_distance_matrix


def _get_area_points_z_s(
    map_name: str,
) -> tuple[dict[str, list[tuple[float, float]]], dict[str, list[float]]]:
    """Get the x, y and z coordinates for all areas in all places.

    Args:
        map_name (str): Map to get the coordinates for

    Returns:
        area_points (dict[str, list[tuple[float, float]]]): Dict mapping each place
            to the x and y coordiantes of each area inside it.
        z_s  (dict[str, list]): Dict mapping each place to the z coordinates of each
            area inside it.
    """
    area_points: dict[str, list[tuple[float, float]]] = defaultdict(list)
    z_s: dict[str, list[float]] = defaultdict(list)
    for area_id in NAV[map_name]:
        area = NAV[map_name][area_id]
        cur_x = [area["southEastX"], area["northWestX"]]
        cur_y = [area["southEastY"], area["northWestY"]]
        # Get the z coordinates for each tile of a named area
        z_s[area["areaName"]].append(area["northWestZ"])
        z_s[area["areaName"]].append(area["southEastZ"])
        # Get all the (x,y) points that make up each tile of a named area
        for x, y in itertools.product(cur_x, cur_y):
            area_points[area["areaName"]].append((x, y))
    return area_points, z_s


def generate_centroids(
    map_name: str,
) -> tuple[dict[str, int], dict[str, int]]:
    """For each region in the given map calculates the centroid and a repr. point.

    Also finds the closest tile for each.

    Args:
        map_name (string): Name of the map for which to calculate the centroids

    Returns:
        Tuple of dictionaries containing the centroid and representative tiles
        for each region of the map

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    area_points, z_s = _get_area_points_z_s(map_name)
    area_ids_cent: dict[str, int] = {}
    area_ids_rep: dict[str, int] = {}
    # For each named area
    for area_name in area_points:
        # Get the (approximate) orthogonal convex hull
        hull = np.array(stepped_hull(area_points[area_name]))
        # Get the centroids and rep. point of the hull
        try:
            my_polygon = Polygon(hull)
            my_centroid = [
                *list(np.array(my_polygon.centroid.coords)[0]),
                mean(z_s[area_name]),
            ]
            rep_point = [
                *list(np.array(my_polygon.representative_point().coords)[0]),
                mean(z_s[area_name]),
            ]
        except ValueError:  # A LinearRing must have at least 3 coordinate tuples
            my_centroid = [
                mean([x for (x, _) in hull]),
                mean([y for (_, y) in hull]),
                mean(z_s[area_name]),
            ]
            rep_point = my_centroid

        # Find the closest tile for these points
        area_ids_cent[area_name] = find_closest_area(map_name, my_centroid)["areaId"]
        area_ids_rep[area_name] = find_closest_area(map_name, rep_point)["areaId"]
    return area_ids_cent, area_ids_rep


def stepped_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Produces an approximation of the orthogonal convex hull.

    Args:
        points (list): A list of points given as tuples (x, y)

    Returns:
        A list of points making up the hull or
        four lists of points making up the four quadrants of the hull
    """
    # May be equivalent to the orthogonal convex hull

    points = sorted(set(points))

    if len(points) <= 1:
        return points

    # Get extreme y points
    min_y = min(points, key=lambda p: p[1])
    max_y = max(points, key=lambda p: p[1])

    # Create upper section
    upper_left = build_stepped_upper(
        sorted(points, key=lambda tup: (tup[0], tup[1])), max_y
    )
    upper_right = build_stepped_upper(
        sorted(points, key=lambda tup: (-tup[0], tup[1])), max_y
    )

    # Create lower section
    lower_left = build_stepped_lower(
        sorted(points, key=lambda tup: (tup[0], -tup[1])), min_y
    )
    lower_right = build_stepped_lower(
        sorted(points, key=lambda tup: (-tup[0], -tup[1])), min_y
    )

    # Correct the ordering
    lower_right.reverse()
    upper_left.reverse()

    # Remove duplicate points
    hull = list(dict.fromkeys(lower_left + lower_right + upper_right + upper_left))
    hull.append(hull[0])
    return hull


def build_stepped_upper(
    points: list[tuple[float, float]], max_y: tuple[float, float]
) -> list[tuple[float, float]]:
    """Builds towards the upper part of the hull.

    Based on starting point and maximum y value.

    Args:
        points (list[tuple[float, float]]): A list of points to build
            the upper left hull section from
        max_y (tuple[float, float]): The point with the highest y

    Returns:
        A list of points making up the upper part of the hull
    """
    # Steps towards the highest y point

    section = [points[0]]

    if max_y != points[0]:
        for point in points:
            if point[1] >= section[-1][1]:
                section.append(point)
            if max_y == point:
                break
    return section


def build_stepped_lower(
    points: list[tuple[float, float]], min_y: tuple[float, float]
) -> list[tuple[float, float]]:
    """Builds towards the lower part of the hull.

    Based on starting point and maximum y value.

    Args:
        points (list[tuple[float, float]]): A list of points to build
            the upper left hull section from
        min_y (tuple[float, float]): The point with the lowest y

    Returns:
        A list of points making up the lower part of the hull
    """
    # Steps towards the lowest y point

    section = [points[0]]

    if min_y != points[1]:
        for point in points:
            if point[1] <= section[-1][1]:
                section.append(point)

            if min_y == point:
                break
    return section


def _check_arguments_position_distance(
    map_name: str,
    position_array_1: npt.NDArray,
    position_array_2: npt.NDArray,
    distance_type: DistanceType = "geodesic",
) -> tuple[npt.NDArray, npt.NDArray]:
    """Check arguments of `position_state_distance`.

    Checks if arguments are valid and raises ValueErrors if not.
    Also orders position_arrays such that position_array_1 never contains
    fewer alive players than position_array_2.

    Args:
        map_name (string): Map to consider
        position_array_1 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the player
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        position_array_2 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the playe
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        distance_type (string, optional): String indicating how the distance between
            two player positions should be calculated.

    Raises:
        ValueError: If map_name is not in awpy.data.NAV.
        ValueError: If distance_type is not one of ["graph", "geodesic", "euclidean"].
        ValueError: If the 0th (number of teams) and 2nd (number of features) dimensions
                        of the inputs do not have the same size.
        ValueError: If number of features is not 3 for euclidean distance_type

    Returns:
       tuple[npt.NDArray, npt.NDArray]: Potentially reordered position arrays.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if distance_type not in get_args(DistanceType):
        msg = "distance_type can only be graph, geodesic or euclidean"
        raise ValueError(msg)
    if (
        position_array_1.shape[0] != position_array_2.shape[0]
        or position_array_1.shape[2] != position_array_2.shape[2]
    ):
        msg = (
            "Game state shapes do not match! "
            "Both states have to have the same number of teams (1 or 2) "
            "and same number of coordinates."
        )
        raise ValueError(msg)
    # Three dimensional space. Unlikely to change anytime soon
    if (
        distance_type not in ["geodesic", "graph"]
        and position_array_1.shape[2] != 3  # noqa: PLR2004
    ):
        msg = (
            "Game state shapes are incorrect! "
            "Both states have to have the same number of coordinates (3)"
            " when not using 'geodesic' or graph 'distance'."
        )
        raise ValueError(msg)
    # Make sure array1 is the one with more players alive
    if position_array_1.shape[1] < position_array_2.shape[1]:
        position_array_1, position_array_2 = position_array_2, position_array_1
    return position_array_1, position_array_2


def _precompute_area_names(
    map_name: str, position_array_1: npt.NDArray, position_array_2: npt.NDArray
) -> dict[int, dict[int, dict]]:
    """Precompute the area names for each player position.

    Args:
        map_name (string): Map to consider
        position_array_1 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the player
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        position_array_2 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the playe
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance

    Returns:
        dict[int, defaultdict[int, dict]]: Mapping for each team
            containing the areaId for each player.
    """
    areas: dict[int, dict[int, dict[int, int]]] = {
        1: defaultdict(dict),
        2: defaultdict(dict),
    }
    if position_array_1.shape[-1] == 3:  # noqa: PLR2004
        for team in range(position_array_1.shape[0]):
            for player in range(position_array_1.shape[1]):
                areas[1][team][player] = find_closest_area(
                    map_name, position_array_1[team][player]
                )["areaId"]
            for player in range(position_array_2.shape[1]):
                areas[2][team][player] = find_closest_area(
                    map_name, position_array_2[team][player]
                )["areaId"]
    else:
        areas[1] = {
            team: {player: int(features[0]) for player, features in enumerate(row)}
            for team, row in enumerate(position_array_1)
        }
        areas[2] = {
            team: {player: int(features[0]) for player, features in enumerate(row)}
            for team, row in enumerate(position_array_2)
        }
    return areas


def _euclidean_position_distance(
    position_array_1: npt.NDArray,
    position_array_2: npt.NDArray,
    team: int,
    player1: int,
    player2: int,
) -> float:
    """Calculate euclidean distance between two players.

    Calculate the euclidean distance between player1 and player2 on `team` for
    position_array_1 vs position_array_2.
    Fast but ignores walls.

    Args:
        position_array_1 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the player
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        position_array_2 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the playe
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        team (int): Which team to consider
        player1 (int): First player in distance calculation
        player2 (int): Second player in distance calculation

    Returns:
        float: Euclidean distance between player1 and player2 in team.
    """
    return math.sqrt(
        (position_array_1[team][player1][0] - position_array_2[team][player2][0]) ** 2
        + (position_array_1[team][player1][1] - position_array_2[team][player2][1]) ** 2
        + (position_array_1[team][player1][2] - position_array_2[team][player2][2]) ** 2
    )


def _graph_based_position_distance(
    map_name: str,
    area1: int,
    area2: int,
    distance_type: DistanceType,
) -> float:
    """Calculate graph based distance between two areas.

    Takes into account the actual map
    The underlying graph is directed
    (There is a short path to drop down a ledge
    but a long one is needed to get back up)
    So calculate both possible values and take the minimum one so
    that the distance between two states/trajectories is commutative

    Args:
        map_name (string): Map to consider
        area1 (int): First area in distance calculation
        area2 (int): Second area in distance calculation
        distance_type (string, optional): String indicating how the distance between
            two player positions should be calculated.
            Options are "geodesic", "graph".

    Returns:
        float: Graph based distance between two areas.
    """
    if map_name not in AREA_DIST_MATRIX:
        this_dist = min(
            area_distance(
                map_name,
                area1,
                area2,
                dist_type=distance_type,
            )["distance"],
            area_distance(
                map_name,
                area2,
                area1,
                dist_type=distance_type,
            )["distance"],
        )
    else:
        this_dist = min(
            AREA_DIST_MATRIX[map_name][str(area1)][str(area2)][distance_type],
            AREA_DIST_MATRIX[map_name][str(area2)][str(area1)][distance_type],
        )
    if this_dist == float("inf"):
        this_dist = sys.maxsize / 6
    return this_dist


def position_state_distance(
    map_name: str,
    position_array_1: npt.NDArray,
    position_array_2: npt.NDArray,
    distance_type: DistanceType = "geodesic",
) -> float:
    """Calculates a distance between two game states based on player positions.

    Args:
        map_name (string): Map to consider
        position_array_1 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the player
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        position_array_2 (numpy array): Numpy array with shape (2|1, 5, 3)
            with the first index indicating the team, the second the playe
            and the third the coordinate.
            Alternatively the array can have shape (2|1, 5, 1) where the last value
            gives the area_id. Used only with geodesic and graph distance
        distance_type (string, optional): String indicating how the distance between
            two player positions should be calculated.
            Options are "geodesic", "graph" and "euclidean". Defaults to 'geodesic'

    Returns:
        A float representing the distance between these two game states

    Raises:
        ValueError: If map_name is not in awpy.data.NAV.
        ValueError: If distance_type is not one of ["graph", "geodesic", "euclidean"].
        ValueError: If the 0th (number of teams) and 2nd (number of features) dimensions
                        of the inputs do not have the same size.
        ValueError: If number of features is not 3 for euclidean distance_type
    """
    position_array_1, position_array_2 = _check_arguments_position_distance(
        map_name, position_array_1, position_array_2, distance_type
    )
    pos_distance: float = 0
    # Pre compute the area names for each player's position
    # If the x,y and z coordinate are given
    # Three dimensional space. Unlikely to change anytime soon
    areas: dict[int, dict[int, dict]] = {}
    if distance_type in ["geodesic", "graph"]:
        areas = _precompute_area_names(map_name, position_array_1, position_array_2)
    # Get the minimum mapping distance for each side separately
    for team in range(position_array_1.shape[0]):
        side_distance = float("inf")
        # Generate all possible mappings between players from array1 and array2.
        # Map player1 from array1 to player1 from array2 and
        # player2's to each other or match player1's with player2's and so on
        for mapping in itertools.permutations(
            range(position_array_1.shape[1]), position_array_2.shape[1]
        ):
            cur_dist: float = 0
            for player2, player1 in enumerate(mapping):
                this_dist = 0
                if distance_type == "euclidean":
                    this_dist = _euclidean_position_distance(
                        position_array_1, position_array_2, team, player1, player2
                    )
                elif distance_type in ["geodesic", "graph"]:
                    area1 = areas[1][team][player1]
                    area2 = areas[2][team][player2]
                    this_dist = _graph_based_position_distance(
                        map_name, area1, area2, distance_type
                    )
                cur_dist += this_dist / len(mapping)
            side_distance = min(side_distance, cur_dist)
        pos_distance += side_distance / position_array_1.shape[0]
    return pos_distance


def _check_arguments_token_distance(
    map_name: str,
    token_array_1: npt.NDArray,
    token_array_2: npt.NDArray,
    distance_type: Literal[DistanceType, "edit_distance"] = "geodesic",
    reference_point: Literal["centroid", "representative_point"] = "centroid",
) -> None:
    """Check arguments of `token_state_distance`.

    Checks if arguments are valid and raises ValueErrors if not.

    Args:
        map_name (string): Map to consider
        token_array_1 (numpy array): 1-D numpy array of a position token
        token_array_2 (numpy array): 1-D numpy array of a position token
        distance_type (string, optional): String indicating how the distance
            between two player positions should be calculated.
            Options are "geodesic", "graph", "euclidean" and "edit_distance".
            Defaults to 'geodesic'
        reference_point (string, optional): String indicating which reference point
            to use to determine area distance.
            Options are "centroid" and "representative_point".
            Defaults to 'centroid'
    Raises:
        ValueError: If map_name is not in awpy.data.NAV.
        ValueError: If distance_type is not one of:
                        ["graph", "geodesic", "euclidean", "edit_distance"]
        ValueError: If reference_point is not one of:
                        ["centroid", "representative_point"]
        ValueError: If the input token arrays do not have the same length.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if distance_type not in ["graph", "geodesic", "euclidean", "edit_distance"]:
        msg = "distance_type can only be graph, geodesic, euclidean or edit_distance"
        raise ValueError(msg)
    if reference_point not in ["centroid", "representative_point"]:
        msg = "reference_point can only be centroid or representative_point"
        raise ValueError(msg)
    if len(token_array_1) != len(token_array_2):
        msg = "Token arrays have to have the same length!"
        raise ValueError(msg)


def _get_map_area_names(map_name: str) -> list[str]:
    """Get the list of named areas.

    Needed to translate back from token position to area name.

    Args:
        map_name (string): Map to consider
        token_array_1 (numpy array): 1-D numpy array of a position token

    Returns:
        list[str]: Sorted list of named areas on the map.
    """
    map_area_names: set[str] = {
        NAV[map_name][area_id]["areaName"] for area_id in NAV[map_name]
    }
    return sorted(map_area_names)


def _check_proper_token_length(
    map_area_names: list[str], token_array: npt.NDArray
) -> None:
    """Checks that the length of the token array matches expectation.

    Args:
        map_area_names (list[str]): Map to consider
        token_array (npt.NDArray): 1-D numpy array of a position token

    Raises:
        ValueError: If the length of the token arrays do not match
                        the expected length for that map.
    """
    if len(token_array) not in [len(map_area_names), len(map_area_names) * 2]:
        msg = (
            "Token arrays do not have the correct length. "
            "There has to be one entry per named area per team considered!"
        )
        raise ValueError(msg)


def _edit_distance_tokens(
    token_array_1: npt.NDArray[np.int_],
    token_array_2: npt.NDArray[np.int_],
    nom_token_length: int,
) -> float:
    """Calculate the edit distance between two token arrays.

    How many edits of one value by 1 (up or down)
    are needed to go from one array to the other
    Eg: [3,0,0] to [0,1,0] needs 4 edits.
    Three to get the first index from 3 to 0
    and then one to get the second from 0 to 1

    Args:
        token_array_1 (numpy array): 1-D numpy array of a position token
        token_array_2 (numpy array): 1-D numpy array of a position token
        nom_token_length (int): Length of a position token for one side

    Returns:
        float: Edit distance between two token arrays
    """
    token_dist: float = sum(map(abs, np.subtract(token_array_1, token_array_2)))
    token_dist /= len(token_array_1) // nom_token_length
    return token_dist


def _get_index_differences(
    token_array_1: npt.NDArray[np.int_],
    token_array_2: npt.NDArray[np.int_],
    map_area_names: list[str],
    team_index: int,
) -> tuple[list[int], list[int], int]:
    """Get indinices that differ between two array.

    Build separate lists for indices where array1/array2 has a larger values.
    Each index ends up in list as many times are the difference of values.

    Args:
        token_array_1 (numpy array): 1-D numpy array of a position token
        token_array_2 (numpy array): 1-D numpy array of a position token
        map_area_names (list[str]): Sorted list of named areas on the map.
        team_index (int): Which team is currently being considered. First or second.

    Returns:
        tuple[list[int], list[int], int]: Lists of differing indices and
            Sum of the smaller array.
    """
    array1, array2, size = _clean_token_arrays(
        token_array_1, token_array_2, map_area_names, team_index=team_index
    )
    # Get the indices where array1 and array2 have larger values than the other.
    # Use each index as often as it if larger
    diff_array = np.subtract(array1, array2)
    pos_indices: list[int] = []
    neg_indices: list[int] = []
    for differing_index, difference in enumerate(diff_array):
        if difference > 0:
            pos_indices.extend([differing_index] * int(difference))
        elif difference < 0:
            neg_indices.extend([differing_index] * int(abs(difference)))
    return pos_indices, neg_indices, size


def _clean_token_arrays(
    token_array_1: npt.NDArray[np.int_],
    token_array_2: npt.NDArray[np.int_],
    map_area_names: list[str],
    team_index: int,
) -> tuple[npt.NDArray[np.int_], npt.NDArray[np.int_], int]:
    """Clean the token arrays used to calculate a token state distance.

    Extract the sub array for the currently considered team,
    make sure array1 is the larger one and
    get the normalization factor for the distance.

    The normalization factor is the sum of the smaller array as the
    a distance is calculated for each player in the smaller array
    and the distance per player pair is desired.

    Args:
        token_array_1 (numpy array): 1-D numpy array of a position token
        token_array_2 (numpy array): 1-D numpy array of a position token
        map_area_names (list[str]): Sorted list of named areas on the map.
        team_index (int): Which team is currently being considered. First or second.

    Returns:
        array1 (numpy array): 1-D numpy array of a position sub token.
        array2 (numpy array): 1-D numpy array of a position sub token.
        size (int): Sum of the smaller array.
    """
    array1, array2 = (
        token_array_1[
            team_index * len(map_area_names) : len(map_area_names)
            + team_index * len(map_area_names),
        ],
        token_array_2[
            team_index * len(map_area_names) : len(map_area_names)
            + team_index * len(map_area_names),
        ],
    )
    # Make sure array1 is the larger one
    if sum(array1) < sum(array2):
        array1, array2 = array2, array1
    size = sum(array2)
    return array1, array2, size


def token_state_distance(
    map_name: str,
    token_array_1: npt.NDArray[np.int_],
    token_array_2: npt.NDArray[np.int_],
    distance_type: Literal[DistanceType, "edit_distance"] = "geodesic",
    reference_point: Literal["centroid", "representative_point"] = "centroid",
) -> float:
    """Calculates a distance between two game states based on player positions.

    Args:
        map_name (string): Map to consider
        token_array_1 (numpy array): 1-D numpy array of a position token
        token_array_2 (numpy array): 1-D numpy array of a position token
        distance_type (string, optional): String indicating how the distance
            between two player positions should be calculated.
            Options are "geodesic", "graph", "euclidean" and "edit_distance".
            Defaults to 'geodesic'
        reference_point (string, optional): String indicating which reference point
            to use to determine area distance.
            Options are "centroid" and "representative_point".
            Defaults to 'centroid'

    Returns:
        A float representing the distance between these two game states

    Raises:
        ValueError: If map_name is not in awpy.data.NAV.
        ValueError: If distance_type is not one of:
                        ["graph", "geodesic", "euclidean", "edit_distance"]
        ValueError: If reference_point is not one of:
                        ["centroid", "representative_point"]
        ValueError: If the input token arrays do not have the same length.
        ValueError: If the length of the token arrays do not match
                        the expected length for that map.
    """
    _check_arguments_token_distance(
        map_name, token_array_1, token_array_2, distance_type, reference_point
    )
    # Get the list of named areas.
    # Needed to translate back from token position to area name
    map_area_names = _get_map_area_names(map_name)
    _check_proper_token_length(map_area_names, token_array_1)

    if distance_type == "edit_distance":
        return _edit_distance_tokens(token_array_1, token_array_2, len(map_area_names))

    # If we do not have the precomputed matrix
    # we need to first build the centroids to get them ourselves later
    ref_points = {}

    if map_name not in PLACE_DIST_MATRIX:
        (
            ref_points["centroid"],
            ref_points["representative_point"],
        ) = generate_centroids(map_name)
    # Loop over each team
    token_dist: float = 0
    for i in range(len(token_array_1) // len(map_area_names)):
        side_distance = float("inf")
        # Get the sub arrays for this team from the total array
        pos_indices, neg_indices, size = _get_index_differences(
            token_array_1, token_array_2, map_area_names, team_index=i
        )
        # Get all possible mappings between the differences
        # Eg: diff array is [1,1,-1,-1]
        # then pos_indices is [0,1] and neg_indices is [2,3]
        # The possible mappings are then [(0,2),(1,3)] and [(0,3),(1,2)]
        for mapping in (
            list(zip(x, neg_indices, strict=True))
            for x in multiset_permutations(pos_indices, len(neg_indices))
        ):
            this_dist: float = sum(
                min(
                    (
                        area_distance(
                            map_name,
                            ref_points[reference_point][map_area_names[area1]],
                            ref_points[reference_point][map_area_names[area2]],
                            dist_type=distance_type,
                        )["distance"],
                        area_distance(
                            map_name,
                            ref_points[reference_point][map_area_names[area2]],
                            ref_points[reference_point][map_area_names[area1]],
                            dist_type=distance_type,
                        )["distance"],
                    )
                    if map_name not in PLACE_DIST_MATRIX
                    else (
                        PLACE_DIST_MATRIX[map_name][map_area_names[area1]][
                            map_area_names[area2]
                        ][distance_type][reference_point],
                        PLACE_DIST_MATRIX[map_name][map_area_names[area2]][
                            map_area_names[area1]
                        ][distance_type][reference_point],
                    )
                )
                for area1, area2 in mapping
            )

            side_distance = min(side_distance, this_dist / size)
        token_dist += side_distance / (len(token_array_1) // len(map_area_names))
    return token_dist


def get_array_for_frame(frame: GameFrame) -> npt.NDArray:
    """Generates a numpy array with the correct dimensions and content for a gameframe.

    Args:
        frame (GameFrame): A game frame

    Returns:
        numpy array for that frame
    """
    pos_array = np.zeros(
        (
            2,
            max(len(frame["ct"]["players"] or []), len(frame["t"]["players"] or [])),
            3,
        )
    )
    team_to_index: dict[Literal["t", "ct"], Literal[0, 1]] = {"t": 0, "ct": 1}
    for team_name, team_index in team_to_index.items():
        for player_index, player in enumerate(frame[team_name]["players"] or []):
            pos_array[team_index][player_index][0] = player["x"]
            pos_array[team_index][player_index][1] = player["y"]
            pos_array[team_index][player_index][2] = player["z"]
    return pos_array


def frame_distance(
    map_name: str,
    frame1: GameFrame,
    frame2: GameFrame,
    distance_type: DistanceType = "geodesic",
) -> float:
    """Calculates a distance between two frames based on player positions.

    Args:
        map_name (string): Map to consider
        frame1 (GameFrame): A game frame
        frame2 (GameFrame): A game frame
        distance_type (string, optional): String indicating how the distance between
            two player positions should be calculated.
            Options are "geodesic", "graph" and "euclidean"
            Defaults to 'geodesic'

    Returns:
        A float representing the distance between these two game states

    Raises:
        ValueError: Raises a ValueError if there is a discrepancy between
                        the frames regarding which sides are filled.
                    If the ct side of frame1 contains players
                        while that of frame2 is empty or None the error will be raised.
                    The same happens for the t sides.
    """
    if (
        (len(frame1["ct"]["players"] or []) > 0)
        != (len(frame2["ct"]["players"] or []) > 0)
    ) or (
        (len(frame1["t"]["players"] or []) > 0)
        != (len(frame2["t"]["players"] or []) > 0)
    ):
        msg = "The active sides between the two frames have to match."
        raise ValueError(msg)
    pos_array1 = get_array_for_frame(frame1)
    pos_array2 = get_array_for_frame(frame2)
    # position_state distance averages the result over the teams
    # However here we are always passing it the values for both team
    # This means if one side is empty and
    # we only want to consider the other one the result is halfed
    # So in that case we multiply the result back with 2
    # Only need to look at one frame here because
    # `position_state_distance` will throw an error
    # anyway if the number of teams does not match between the frames
    team_number_multipler = (
        1
        if (len(frame2["ct"]["players"] or []) > 0)
        and (len(frame2["t"]["players"] or []) > 0)
        else 2
    )

    return (
        position_state_distance(map_name, pos_array1, pos_array2, distance_type)
        * team_number_multipler
    )


def token_distance(
    map_name: str,
    token1: str,
    token2: str,
    distance_type: Literal[DistanceType, "edit_distance"] = "geodesic",
    reference_point: Literal["centroid", "representative_point"] = "centroid",
) -> float:
    """Calculates a distance between two game states based on position tokens.

    Args:
        map_name (string): Map to consider
        token1 (string): A team position token
        token2 (string): A team position token
        distance_type (string, optional): String indicating how the distance between
            two player positions should be calculated.
            Options are "geodesic", "graph", "euclidean" and "edit_distance".
            Defaults to 'geodesic'
        reference_point (string, optional): String indicating which reference point
            to use to determine area distance.
            Options are "centroid" and "representative_point".
            Defaults to 'centroid'

    Returns:
        A float representing the distance between these two game states
    """
    return token_state_distance(
        map_name,
        np.array(list(token1), dtype=int),
        np.array(list(token2), dtype=int),
        distance_type,
        reference_point,
    )


def calculate_tile_area(
    map_name: str,
    tile_id: TileId,
) -> float:
    """Calculates area of a given tile in a given map.

    Args:
        map_name (string): Map for tile
        tile_id (TileId): Id for tile

    Returns:
        A float representing the area of the tile

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If area_id is not in awpy.data.NAV[map_name]
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if tile_id not in NAV[map_name]:
        msg = "Tile ID not found."
        raise ValueError(msg)

    tile_info = NAV[map_name][tile_id]

    tile_width = tile_info["northWestX"] - tile_info["southEastX"]
    tile_height = tile_info["northWestY"] - tile_info["southEastY"]

    return tile_width * tile_height


def calculate_map_area(
    map_name: str,
) -> float:
    """Calculates total area of all nav tiles in a given map.

    Args:
        map_name (string): Map for area calculations

    Returns:
        A float representing the area of the map

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    total_area = 0
    for tile in NAV[map_name]:
        total_area += calculate_tile_area(map_name, tile)

    return total_area
