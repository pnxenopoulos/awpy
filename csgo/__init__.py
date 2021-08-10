import lzma
import os
import pickle
import pandas as pd

# import brotli

from csgo.utils import AutoVivification

path = os.path.join(os.path.dirname(__file__), "")
DIST = pickle.load(lzma.open(path + "data/nav/distances.xz", "rb"))
MAP_NAV = pd.read_csv(path + "data/nav/map_nav.csv")
