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
CURRENT_BUILD_ID = 17595823
AVAILABLE_PATCHES = {
    17595823: {
        "url": "https://steamdb.info/patchnotes/17595823/",
        "datetime": datetime.datetime.fromtimestamp(1741128785, datetime.UTC),
        "available": POSSIBLE_ARTIFACTS,
    }
}
