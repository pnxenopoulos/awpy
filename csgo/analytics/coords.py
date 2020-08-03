""" Coordinate conversion functions for csgo
"""

import os
import subprocess
import numpy as np


def coords_to_area(x=0, y=0, z=0, map="de_dust2"):
    """ Returns a dicitonary of the area 

    Args:
        x (float) : X coordinate
        y (float) : Y coordinate
        z (float) : Z coordinate
        map (string) : Map name as a string
    """
    if map not in [
        "de_dust2",
        "de_cbble",
        "de_inferno",
        "de_mirage",
        "de_nuke",
        "de_overpass",
        "de_train",
        "de_vertigo",
    ]:
        raise ValueError(
            f'Invalid map name: got {map}, expected one of: "de_dust2", "de_cbble", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train", "de_vertigo"'
        )
    path = os.path.join(os.path.dirname(__file__), "")
    proc = subprocess.Popen(
        [
            "go",
            "run",
            "coords_to_area.go",
            "-map",
            map,
            "-x",
            str(x),
            "-y",
            str(y),
            "-z",
            str(z),
        ],
        stdout=subprocess.PIPE,
        cwd=path,
    )
    output_string = str(proc.stdout.read().decode("utf-8"))
    output = {}
    output["AreaId"] = int(output_string.split("[")[0].strip().split(":")[1].strip())
    output["AreaName"] = output_string.split("[")[1].strip().split("]")[0]
    return output
