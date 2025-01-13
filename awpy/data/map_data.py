"""Dictionary that holds map data for Counter-Strike 2."""

import ast
from pathlib import Path
from typing import TypedDict

import vdf


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
    file_path = Path(__file__)
    with file_path.open("r") as file:
        tree = ast.parse(file.read())

    class MapDataUpdater(ast.NodeTransformer):
        def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
            if isinstance(node.target, ast.Name) and node.target.id == "MAP_DATA":
                node.value = (
                    ast.parse(repr(new_map_data).replace("-inf", 'float("-inf")'))
                    .body[0]
                    .value
                )
                print(ast.dump(node.value, indent=4))
            return node

    updater = MapDataUpdater()
    updated_tree = updater.visit(tree)
    with file_path.open("w") as file:
        file.write(ast.unparse(updated_tree))


MAP_DATA: dict[str, MapDataType] = {
    "ar_baggage": {
        "pos_x": -1316,
        "pos_y": 1288,
        "scale": 2.539062,
        "rotate": 1,
        "zoom": 1.3,
        "lower_level_max_units": -5.0,
    },
    "ar_shoots": {
        "pos_x": -1368,
        "pos_y": 1952,
        "scale": 2.6875,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": float("-inf"),
    },
    "cs_italy": {
        "pos_x": -2647,
        "pos_y": 2592,
        "scale": 4.6,
        "rotate": 1,
        "zoom": 1.5,
        "lower_level_max_units": float("-inf"),
    },
    "cs_office": {
        "pos_x": -1838,
        "pos_y": 1858,
        "scale": 4.1,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": float("-inf"),
    },
    "de_ancient": {
        "pos_x": -2953,
        "pos_y": 2164,
        "scale": 5.0,
        "rotate": 0,
        "zoom": 0.0,
        "lower_level_max_units": float("-inf"),
    },
    "de_anubis": {
        "pos_x": -2796,
        "pos_y": 3328,
        "scale": 5.22,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": float("-inf"),
    },
    "de_dust": {
        "pos_x": -2850,
        "pos_y": 4073,
        "scale": 6.0,
        "rotate": 1,
        "zoom": 1.3,
        "lower_level_max_units": float("-inf"),
    },
    "de_dust2": {
        "pos_x": -2476,
        "pos_y": 3239,
        "scale": 4.4,
        "rotate": 1,
        "zoom": 1.1,
        "lower_level_max_units": float("-inf"),
    },
    "de_inferno": {
        "pos_x": -2087,
        "pos_y": 3870,
        "scale": 4.9,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": float("-inf"),
    },
    "de_mirage": {
        "pos_x": -3230,
        "pos_y": 1713,
        "scale": 5.0,
        "rotate": 0,
        "zoom": 0.0,
        "lower_level_max_units": float("-inf"),
    },
    "de_nuke": {
        "pos_x": -3453,
        "pos_y": 2887,
        "scale": 7.0,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": -495.0,
    },
    "de_overpass": {
        "pos_x": -4831,
        "pos_y": 1781,
        "scale": 5.2,
        "rotate": 0,
        "zoom": 0.0,
        "lower_level_max_units": float("-inf"),
    },
    "de_train": {
        "pos_x": -2308,
        "pos_y": 2078,
        "scale": 4.082077,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": -50.0,
    },
    "de_vertigo": {
        "pos_x": -3168,
        "pos_y": 1762,
        "scale": 4.0,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": 11700.0,
    },
    "workshop_preview": {
        "pos_x": -2071,
        "pos_y": 711,
        "scale": 1.699219,
        "rotate": None,
        "zoom": None,
        "lower_level_max_units": float("-inf"),
    },
}
