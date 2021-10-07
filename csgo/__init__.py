import json
import lzma
import os
import pickle
import pandas as pd

from pathlib import Path

# import brotli

path = os.path.join(os.path.dirname(__file__), "")

DIST = pickle.load(lzma.open(path + "data/nav/distances.xz", "rb"))
MAP_NAV = pd.read_csv(path + "data/nav/map_nav.csv")

with open(Path(path + "data/map/map_data.json")) as f:
    MAP_DATA = json.load(f)

side_colors = {"ct": "#5d79ae", "t": "#de9b35"}
