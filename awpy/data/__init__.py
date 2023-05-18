"""Provides data such as radar images and navigation meshes."""
import json
import os
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import distance

from awpy.types import Area, AreaMatrix, MapData, PlaceMatrix
from awpy.utils import transform_csv_to_json

PATH = os.path.join(os.path.dirname(__file__), "")

NAV_CSV = pd.read_csv(PATH + "nav/nav_info.csv")
NAV_CSV.areaName = NAV_CSV.areaName.fillna("")


NAV: dict[str, dict[int, Area]] = transform_csv_to_json(NAV_CSV)


def create_nav_graphs(
    nav: dict[str, dict[int, Area]], data_path: str
) -> dict[str, nx.DiGraph]:
    """Function to create a dict of DiGraphs from dict of areas and edge_list file.

    Args:
        nav (dict): Dictionary containing information about each area of each map
        data_path (str): Path to the awpy.data folder containing navigation and map data

    Returns:
        A dictionary mapping each map (str) to an nx.DiGraph of its traversible areas
    """
    nav_graphs: dict[str, nx.DiGraph] = {}
    for map_name in nav:
        map_graph = nx.DiGraph()
        for area_id in nav[map_name]:
            area = nav[map_name][area_id]
            map_graph.add_nodes_from(
                [
                    (
                        area_id,
                        {
                            "mapName": map_name,
                            "areaID": area_id,
                            "areaName": area["areaName"],
                            "northWestX": area["northWestX"],
                            "northWestY": area["northWestY"],
                            "northWestZ": area["northWestZ"],
                            "southEastX": area["southEastX"],
                            "southEastY": area["southEastY"],
                            "southEastZ": area["southEastZ"],
                            "center": [
                                (area["northWestX"] + area["southEastX"]) / 2,
                                (area["northWestY"] + area["southEastY"]) / 2,
                                (area["northWestZ"] + area["southEastZ"]) / 2,
                            ],
                            "size": np.sqrt(
                                (area["northWestX"] - area["southEastX"]) ** 2
                                + (area["northWestY"] - area["southEastY"]) ** 2
                                + (area["northWestZ"] - area["southEastZ"]) ** 2
                            ),
                        },
                    ),
                ]
            )
        with open(
            os.path.join(data_path, "nav", f"{map_name}.txt"), encoding="utf8"
        ) as edge_list:
            edge_list_lines = edge_list.readlines()
        for line in edge_list_lines:
            areas = line.strip().split(",")
            map_graph.add_edge(
                int(areas[0]),
                int(areas[1]),
                weight=distance.euclidean(
                    map_graph.nodes[int(areas[0])]["center"],
                    map_graph.nodes[int(areas[1])]["center"],
                ),
            )
        nav_graphs[map_name] = map_graph
    return nav_graphs


NAV_GRAPHS = create_nav_graphs(NAV, PATH)

# Open map data
with open(Path(PATH + "map/map_data.json"), encoding="utf8") as map_data:
    MAP_DATA: dict[str, MapData] = json.load(map_data)


def _get_dist_matrices() -> tuple[dict[str, PlaceMatrix], dict[str, AreaMatrix]]:
    place_dist_matrix: dict[str, PlaceMatrix] = {}
    area_dist_matrix: dict[str, AreaMatrix] = {}
    for file in os.listdir(PATH + "nav/"):
        if file.startswith("place_distance_matrix"):
            this_map_name = "_".join(file.split(".")[0].split("_")[-2:])
            with open(Path(PATH + "nav/" + file), encoding="utf8") as place_dist_data:
                place_dist_matrix[this_map_name] = json.load(place_dist_data)
        elif file.startswith("area_distance_matrix"):
            this_map_name = "_".join(file.split(".")[0].split("_")[-2:])
            with open(Path(PATH + "nav/" + file), encoding="utf8") as area_dist_data:
                area_dist_matrix[this_map_name] = json.load(area_dist_data)
    return place_dist_matrix, area_dist_matrix


PLACE_DIST_MATRIX, AREA_DIST_MATRIX = _get_dist_matrices()
