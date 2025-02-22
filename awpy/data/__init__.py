"""Module to hold Counter-Strike 2 data."""

import datetime
import pathlib

# Data directories
AWPY_DATA_DIR = pathlib.Path.home() / ".awpy"
MAPS_DIR = AWPY_DATA_DIR / "maps"
NAVS_DIR = AWPY_DATA_DIR / "navs"
TRIS_DIR = AWPY_DATA_DIR / "tris"

# Uses build id from https://steamdb.info/app/730/patchnotes/
CURRENT_BUILD_ID = 17459940
AVAILABLE_PATCHES = {
    17459940: {
        "url": "https://steamdb.info/patchnotes/17459940/",
        "datetime": datetime.datetime(2025, 2, 21, 21, 23, 31, tzinfo=datetime.UTC),
        "available": ["maps", "navs", "tris"],
    }
}
