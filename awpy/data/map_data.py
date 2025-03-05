"""Module to create the map data."""

import contextlib
import json
from pathlib import Path
from typing import TypedDict

with contextlib.suppress(ImportError, ModuleNotFoundError):
    import vdf  # This is only used for map data parsing

from loguru import logger

try:
    from awpy.data import MAPS_DIR

    map_data_file = MAPS_DIR / "map-data.json"
    with open(map_data_file) as map_data_file:
        MAP_DATA = json.load(map_data_file)
except Exception as _e:
    logger.warning(f"Failed to load map data from {map_data_file}.")
    MAP_DATA = {}


class VerticalSection(TypedDict):
    """Type for a specified vertical section of a map."""

    altitude_min: float
    altitude_max: float


class MapData(TypedDict):
    """Type of the data for a map. `pos_x` is upper left world coordinate."""

    pos_x: int
    pos_y: int
    scale: float
    rotate: int | None
    zoom: float | None
    vertical_sections: dict[str, VerticalSection]
    lower_level_max_units: float


def map_data_from_vdf_files(vdf_folder: Path) -> dict[str, MapData]:
    """Generate the map data from a vdf file."""
    new_map_data: MapData = {}
    for vdf_file in vdf_folder.iterdir():
        # Skip vanity and previews
        if vdf_file.stem.endswith("vanity") or "_preview_" in vdf_file.stem:
            continue
        parsed_data = vdf.loads(vdf_file.read_text())
        if vdf_file.stem not in parsed_data:
            print(f"Skipping {vdf_file.stem} because the file name is not a valid key.")
            print(f"Keys: {list(parsed_data.keys())}")
            continue
        map_data = parsed_data[vdf_file.stem]
        new_map_data[vdf_file.stem] = {
            "pos_x": int(float(map_data["pos_x"])),
            "pos_y": int(float(map_data["pos_y"])),
            "scale": float(map_data["scale"]),
            "rotate": int(rotate) if (rotate := map_data.get("rotate")) else None,
            "zoom": float(zoom) if (zoom := map_data.get("zoom")) else None,
            "lower_level_max_units": float(
                map_data.get("verticalsections", {})
                .get("lower", {})
                .get("AltitudeMax", -1000000)  # Use instead of infinity
            ),
            "vertical_sections": {
                section_name: {
                    "altitude_min": float(section["AltitudeMin"]),
                    "altitude_max": float(section["AltitudeMax"]),
                }
                for section_name, section in map_data.get("verticalsections", {}).items()
            },
        }
    return dict(sorted(new_map_data.items()))


def update_map_data_file(new_map_data: dict[str, MapData], filepath: Path) -> None:
    """Update the map data file."""
    with open(filepath, "w") as json_file:
        json.dump(new_map_data, json_file)
        json_file.write("\n")
