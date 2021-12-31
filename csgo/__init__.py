import json
import os
import pandas as pd
import numpy as np
import networkx as nx

from csgo.utils import transform_csv_to_json
from pathlib import Path

path = os.path.join(os.path.dirname(__file__), "")

# Create nav tile info
nav_dfs = []
for file in os.listdir(path + "data/nav/"):
    if file.endswith(".csv"):
        df = pd.read_csv(path + "data/nav/" + file)
        if "dust2" in file:
            print("-----")
            print(df.columns)
            print(df[df["areaId"] == 152])
            print("-----")
        nav_dfs.append(df)
NAV_CSV = pd.concat(nav_dfs)
NAV_CSV.areaName = NAV_CSV.areaName.fillna("")
print("-----")
print(NAV_CSV.columns)
print(NAV_CSV[(NAV_CSV["areaId"] == 152) & (NAV_CSV["mapName"] == "de_dust2")])
print(NAV_CSV.index)
print("-----")
NAV = transform_csv_to_json(NAV_CSV)
print(NAV["de_dust2"][152])

# Create nav graphs
NAV_GRAPHS = {}
for m in NAV.keys():
    G = nx.Graph()
    for a in NAV[m].keys():
        r = NAV[m][a]
        G.add_nodes_from([
            (a, {
                "mapName": m,
                "areaID": a, 
                "areaName": r["areaName"], 
                "northWestX": r["northWestX"],
                "northWestY": r["northWestY"],
                "northWestZ": r["northWestZ"],
                "southEastX": r["southEastX"],
                "southEastY": r["southEastY"],
                "southEastZ": r["southEastZ"],
                "size": np.sqrt(
                    (r["northWestX"]-r["southEastX"])**2 +
                    (r["northWestY"]-r["southEastY"])**2 +
                    (r["northWestZ"]-r["southEastZ"])**2
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
