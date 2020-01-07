import os
import subprocess

from scipy.spatial import distance


def point_distance(point_a, point_b, type="graph", map="de_dust2"):
    """ This function returns the distance between two points

    Attributes:
        point_a: A list of floats or ints containing the position of point A
        point_b: A list of floats or ints containing the position of point B
        type: A string that is one of 'euclidean', 'manhattan', 'canberra', 'cosine' or 'graph'. Using 'graph' will use A* to find the shortest path and counts the discrete areas it travels.
        map: A string indicating the map
    """
    if type == "graph":
        path = os.path.join(os.path.dirname(__file__), "path_distance.go")
        proc = subprocess.Popen(
            [
                "go",
                "run",
                path,
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
