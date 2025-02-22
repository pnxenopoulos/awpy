"""Module to hold Counter-Strike 2 data."""

from pathlib import Path

# Data directories
AWPY_DATA_DIR = Path.home() / ".awpy"
MAPS_DIR = AWPY_DATA_DIR / "maps"
NAVS_DIR = AWPY_DATA_DIR / "navs"
TRIS_DIR = AWPY_DATA_DIR / "tris"

# Uses build id from https://steamdb.info/app/730/patchnotes/
CURRENT_BUILD_ID = 17459940
