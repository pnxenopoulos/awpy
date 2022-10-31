import json
import os
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.spatial import distance
import networkx as nx

from awpy.utils import transform_csv_to_json


PATH = os.path.join(os.path.dirname(__file__), "")

# Create nav tile info
nav_dfs = []
for file in os.listdir(PATH + "nav/"):
    if file.endswith(".csv"):
        df = pd.read_csv(PATH + "nav/" + file)
        nav_dfs.append(df)

NAV_CSV = pd.concat(nav_dfs, ignore_index=True)
NAV_CSV.areaName = NAV_CSV.areaName.fillna("")
NAV = transform_csv_to_json(NAV_CSV)

# Create nav graphs
NAV_GRAPHS = {}
for m in NAV:
    G = nx.DiGraph()
    for a in NAV[m].keys():
        r = NAV[m][a]
        G.add_nodes_from(
            [
                (
                    a,
                    {
                        "mapName": m,
                        "areaID": a,
                        "areaName": r["areaName"],
                        "northWestX": r["northWestX"],
                        "northWestY": r["northWestY"],
                        "northWestZ": r["northWestZ"],
                        "southEastX": r["southEastX"],
                        "southEastY": r["southEastY"],
                        "southEastZ": r["southEastZ"],
                        "center": [
                            (r["northWestX"] + r["southEastX"]) / 2,
                            (r["northWestY"] + r["southEastY"]) / 2,
                            (r["northWestY"] + r["southEastY"]) / 2,
                        ],
                        "size": np.sqrt(
                            (r["northWestX"] - r["southEastX"]) ** 2
                            + (r["northWestY"] - r["southEastY"]) ** 2
                            + (r["northWestZ"] - r["southEastZ"]) ** 2
                        ),
                    },
                ),
            ]
        )
    edge_list = open(PATH + "nav/" + m + ".txt", "r", encoding="utf8")
    edge_list_lines = edge_list.readlines()
    for line in edge_list_lines:
        areas = line.strip().split(",")
        G.add_edge(
            int(areas[0]),
            int(areas[1]),
            weight=distance.euclidean(
                G.nodes()[int(areas[0])]["center"], G.nodes()[int(areas[1])]["center"]
            ),
        )
    NAV_GRAPHS[m] = G

# Open map data
with open(Path(PATH + "map/map_data.json"), encoding="utf8") as f:
    MAP_DATA = json.load(f)

PLACE_DIST_MATRIX = {}
AREA_DIST_MATRIX = {}
for file in os.listdir(PATH + "nav/"):
    if file.startswith("place_distance_matrix"):
        this_map_name = "_".join(file.split(".")[0].split("_")[-2:])
        with open(Path(PATH + "nav/" + file), encoding="utf8") as f:
            PLACE_DIST_MATRIX[this_map_name] = json.load(f)
    elif file.startswith("area_distance_matrix"):
        this_map_name = "_".join(file.split(".")[0].split("_")[-2:])
        with open(Path(PATH + "nav/" + file), encoding="utf8") as f:
            AREA_DIST_MATRIX[this_map_name] = json.load(f)
if not AREA_DIST_MATRIX:
    AREA_DIST_MATRIX = None
if not PLACE_DIST_MATRIX:
    PLACE_DIST_MATRIX = None
