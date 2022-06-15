from multiprocessing.sharedctypes import Value
import networkx as nx
import numpy as np

from awpy.data import NAV, NAV_GRAPHS
from scipy.spatial import distance


def point_in_area(map_name, area_id, point):
    """Returns if the point is within a nav area for a map.

    Args:
        map_name (string): Map to search
        area_id (int): Area ID as an integer
        point (list): Point as a list [x,y,z]

    Returns:
        True if area contains the point, false if not
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if area_id not in NAV[map_name].keys():
        raise ValueError("Area ID not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    contains_x = (
        min(NAV[map_name][area_id]["northWestX"], NAV[map_name][area_id]["southEastX"])
        < point[0]
        < max(
            NAV[map_name][area_id]["northWestX"], NAV[map_name][area_id]["southEastX"]
        )
    )
    contains_y = (
        min(NAV[map_name][area_id]["northWestY"], NAV[map_name][area_id]["southEastY"])
        < point[1]
        < max(
            NAV[map_name][area_id]["northWestY"], NAV[map_name][area_id]["southEastY"]
        )
    )
    if contains_x and contains_y:
        return True
    else:
        return False


def find_closest_area(map_name, point):
    """Finds the closest area in the nav mesh. Searches through all the areas by comparing point to area centerpoint.

    Args:
        map_name (string): Map to search
        point (list): Point as a list [x,y,z]

    Returns:
        A dict containing info on the closest area
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    closest_area = {"mapName": map_name, "areaId": None, "distance": 999999}
    for area in NAV[map_name].keys():
        avg_x = (
            NAV[map_name][area]["northWestX"] + NAV[map_name][area]["southEastX"]
        ) / 2
        avg_y = (
            NAV[map_name][area]["northWestY"] + NAV[map_name][area]["southEastY"]
        ) / 2
        avg_z = (
            NAV[map_name][area]["northWestZ"] + NAV[map_name][area]["southEastZ"]
        ) / 2
        dist = np.sqrt(
            (point[0] - avg_x) ** 2 + (point[1] - avg_y) ** 2 + (point[2] - avg_z) ** 2
        )
        if dist < closest_area["distance"]:
            closest_area["areaId"] = area
            closest_area["distance"] = dist
    return closest_area


def area_distance(map_name, area_a, area_b, dist_type="graph"):
    """Returns the distance between two areas. Dist type an be graph or geodesic.

    Args:
        map_name (string): Map to search
        area_a (int): Area id
        area_b (int): Area id
        dist_type (string): String indicating the type of distance to use (graph or geodesic)

    Returns:
        A dict containing info on the path between two areas.
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if (area_a not in NAV[map_name].keys()) or (area_b not in NAV[map_name].keys()):
        raise ValueError("Area ID not found.")
    if dist_type not in ["graph", "geodesic"]:
        raise ValueError("dist_type can only be graph or geodesic")
    G = NAV_GRAPHS[map_name]
    distance_obj = {"distanceType": dist_type, "distance": None, "areas": []}
    if dist_type == "graph":
        discovered_path = nx.shortest_path(G, area_a, area_b)
        distance_obj["distance"] = len(discovered_path) - 1
        distance_obj["areas"] = discovered_path
        return distance_obj
    if dist_type == "geodesic":

        def dist(a, b):
            return G.nodes()[a]["size"] + G.nodes()[b]["size"]

        geodesic_path = nx.astar_path(G, area_a, area_b, heuristic=dist)
        geodesic_cost = 0
        for i, area in enumerate(geodesic_path):
            if i > 0:
                geodesic_cost += G.nodes()[area]["size"]
        distance_obj["distance"] = geodesic_cost
        distance_obj["areas"] = geodesic_path
        return distance_obj


def point_distance(map_name, point_a, point_b, dist_type="graph"):
    """Returns the distance between two points.

    Args:
        map_name (string): Map to search
        point_a (list): Point as a list (x,y,z)
        point_b (list): Point as a list (x,y,z)
        dist_type (string): String indicating the type of distance to use. Can be graph, geodesic, euclidean, manhattan, canberra or cosine.

    Returns:
        A dict containing info on the distance between two points.
    """
    distance_obj = {"distanceType": dist_type, "distance": None, "areas": []}
    if dist_type == "graph":
        if map_name not in NAV.keys():
            raise ValueError("Map not found.")
        if len(point_a) != 3 or len(point_b) != 3:
            raise ValueError(
                "When using graph or geodesic distance, point must be X/Y/Z"
            )
        area_a = find_closest_area(map_name, point_a)["areaId"]
        area_b = find_closest_area(map_name, point_b)["areaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "geodesic":
        if map_name not in NAV.keys():
            raise ValueError("Map not found.")
        if len(point_a) != 3 or len(point_b) != 3:
            raise ValueError(
                "When using graph or geodesic distance, point must be X/Y/Z"
            )
        area_a = find_closest_area(map_name, point_a)["areaId"]
        area_b = find_closest_area(map_name, point_b)["areaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "euclidean":
        distance_obj["distance"] = distance.euclidean(point_a, point_b)
        return distance_obj
    elif dist_type == "manhattan":
        distance_obj["distance"] = distance.cityblock(point_a, point_b)
        return distance_obj
    elif dist_type == "canberra":
        distance_obj["distance"] = distance.canberra(point_a, point_b)
        return distance_obj
    elif dist_type == "cosine":
        distance_obj["distance"] = distance.cosine(point_a, point_b)
        return distance_obj


def generate_position_token(map_name, frame):
    """Generates the position token for a game frame.

    Args:
        map_name (string): Map to search
        frame (dict): A game frame

    Returns:
        A dict containing the T token, CT token and combined token (T + CT concatenated)
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if (len(frame["ct"]["players"]) == 0) or (len(frame["t"]["players"]) == 0):
        raise ValueError("CT or T players has length of 0")
    # Create map area list
    map_area_names = []
    for area_id in NAV[map_name]:
        if NAV[map_name][area_id]["areaName"] not in map_area_names:
            map_area_names.append(NAV[map_name][area_id]["areaName"])
    map_area_names.sort()
    # Create token
    ct_token = np.zeros(len(map_area_names), dtype=np.int8)
    for player in frame["ct"]["players"]:
        if player["isAlive"]:
            closest_area = find_closest_area(
                map_name, [player["x"], player["y"], player["z"]]
            )
            ct_token[
                map_area_names.index(NAV[map_name][closest_area["areaId"]]["areaName"])
            ] += 1
    t_token = np.zeros(len(map_area_names), dtype=np.int8)
    for player in frame["t"]["players"]:
        if player["isAlive"]:
            closest_area = find_closest_area(
                map_name, [player["x"], player["y"], player["z"]]
            )
            t_token[
                map_area_names.index(NAV[map_name][closest_area["areaId"]]["areaName"])
            ] += 1
    # Create payload
    token = {}
    token["tToken"] = (
        str(t_token).replace("'", "").replace("[", "").replace("]", "").replace(" ", "")
    )
    token["ctToken"] = (
        str(ct_token)
        .replace("'", "")
        .replace("[", "")
        .replace("]", "")
        .replace(" ", "")
    )
    token["token"] = token["ctToken"] + token["tToken"]
    return token
