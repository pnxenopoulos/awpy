"""Dictionary that holds map data for Counter-Strike 2."""

import json
from pathlib import Path
from typing import TypedDict

import vdf

_MAP_DATA_PATH = Path(__file__).parent / "maps/map_data.json"


class MapDataType(TypedDict):
    """Type of the data for a map.

    pos_x is upper left world coordinate
    """

    pos_x: int
    pos_y: int
    scale: float
    rotate: int | None
    zoom: float | None
    lower_level_max_units: float


def map_data_from_vdf_files(vdf_folder: Path) -> dict[str, MapDataType]:
    """Generate the map data from a vdf file."""
    new_map_data: MapDataType = {}
    for vdf_file in vdf_folder.iterdir():
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
                .get("AltitudeMax", float("-inf"))
            ),
        }
    return dict(sorted(new_map_data.items()))


def update_map_data_file(new_map_data: dict[str, MapDataType]) -> None:
    """Update the map data file."""
    with open(_MAP_DATA_PATH, "w") as json_file:
        json.dump(new_map_data, json_file)
        json_file.write("\n")


with open(_MAP_DATA_PATH) as json_file:
    MAP_DATA: dict[str, MapDataType] = json.load(json_file)
