""" Distance functions for csgo
"""

import os
import subprocess
import numpy as np

from scipy.spatial import distance


def bombsite_distance(location, bombsite="A", map="de_dust2"):
    """ Returns the distance between a location and a given bombsite

    Attributes:
        Location: A list of floats or ints containing the starting position
        bombsite: A string indicating the bombsite (A or B)
        map: A string indicating the map
    """
    path = os.path.join(os.path.dirname(__file__), "")
    proc = subprocess.Popen(
        [
            "go",
            "run",
            "distance_bombsite.go",
            "-map",
            map,
            "-start_x",
            str(location[0]),
            "-start_y",
            str(location[1]),
            "-start_z",
            str(location[2]),
            "-bombsite",
            bombsite,
        ],
        stdout=subprocess.PIPE,
        cwd=path,
    )
    return int(proc.stdout.read().decode("utf-8"))


def point_distance(point_a, point_b, type="graph", map="de_dust2"):
    """ Returns the distance between two points using a given method on a given map (if needed)

    Attributes:
        point_a: A list of floats or ints containing the position of point A
        point_b: A list of floats or ints containing the position of point B
        type: A string that is one of 'euclidean', 'manhattan', 'canberra', 'cosine' or 'graph'. Using 'graph' will use A* to find the shortest path and counts the discrete areas it travels.
        map: A string indicating the map
    """
    if type == "graph":
        path = os.path.join(os.path.dirname(__file__), "")
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "path_distance.go",
                "-map",
                map,
                "-start_x",
                str(point_a[0]),
                "-start_y",
                str(point_a[1]),
                "-start_z",
                str(point_a[2]),
                "-end_x",
                str(point_b[0]),
                "-end_y",
                str(point_b[1]),
                "-end_z",
                str(point_b[2]),
            ],
            stdout=subprocess.PIPE,
            cwd=path,
        )
        return int(proc.stdout.read())
    elif type == "euclidean":
        return distance.euclidean(point_a, point_b)
    elif type == "manhattan":
        return distance.cityblock(point_a, point_b)
    elif type == "canberra":
        return distance.canberra(point_a, point_b)
    elif type == "cosine":
        return distance.cosine(point_a, point_b)


def polygon_area(x, y):
    """ Returns area of a polygon given x,y coordinates of vertices

    Attributes:
        x: A list of floats indicating x index of vertices
        y: A list of floats indicating y index of vertices
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
