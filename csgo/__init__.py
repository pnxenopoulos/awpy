import json
import os
import pandas as pd
import numpy as np
import networkx as nx

from csgo.utils import transform_csv_to_json

from pathlib import Path

# import brotli

path = os.path.join(os.path.dirname(__file__), "")

# Create nav tile info
nav_dfs = []
for file in os.listdir(path + "data/nav/"):
    if file.endswith(".csv"):
        nav_dfs.append(pd.read_csv(path + "data/nav/" + file))
NAV_CSV = pd.concat(nav_dfs)
NAV = transform_csv_to_json(NAV_CSV)

# Create nav graphs
NAV_GRAPHS = {}
for m in NAV.keys():
    G = nx.Graph()
    for a in NAV[m].keys():
        r = NAV[m][a]
        G.add_nodes_from([
            (a, {
                "MapName": m,
                "AreaID": a, 
                "AreaName": r["AreaName"], 
                "NorthWestX": r["NorthWestX"],
                "NorthWestY": r["NorthWestY"],
                "NorthWestZ": r["NorthWestZ"],
                "SouthEastX": r["SouthEastX"],
                "SouthEastY": r["SouthEastY"],
                "SouthEastZ": r["SouthEastZ"],
                "Size": np.sqrt(
                    (r["NorthWestX"]-r["SouthEastX"])**2 +
                    (r["NorthWestY"]-r["SouthEastY"])**2 +
                    (r["NorthWestZ"]-r["SouthEastZ"])**2
                ),
            }),
        ])
    edge_list = open(path + "data/nav/" + m + ".txt", 'r')
    edge_list_lines = edge_list.readlines()
    for line in edge_list_lines:
        areas = line.strip().split(",")
        G.add_edge(int(areas[0]), int(areas[1]))
    NAV_GRAPHS[m] = G

# Open map data
with open(Path(path + "data/map/map_data.json")) as f:
    MAP_DATA = json.load(f)

side_colors = {"ct": "#5d79ae", "t": "#de9b35"}
