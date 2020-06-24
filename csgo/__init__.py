import lzma
import os
import pickle

# import brotli

from csgo.utils import AutoVivification

path = os.path.join(os.path.dirname(__file__), "")
DIST_DICT = pickle.load(lzma.open(path + "data/nav/distances.xz", "rb"))
