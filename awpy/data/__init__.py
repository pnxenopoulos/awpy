"""Module to hold Counter-Strike 2 data."""

import datetime
import pathlib

# Data directories
AWPY_DATA_DIR = pathlib.Path.home() / ".awpy"
MAPS_DIR = AWPY_DATA_DIR / "maps"
NAVS_DIR = AWPY_DATA_DIR / "navs"
TRIS_DIR = AWPY_DATA_DIR / "tris"

# Uses build id from https://steamdb.info/app/730/patchnotes/
POSSIBLE_ARTIFACTS = ["maps", "navs", "tris"]
CURRENT_BUILD_ID = 0
AVAILABLE_PATCHES = {}
