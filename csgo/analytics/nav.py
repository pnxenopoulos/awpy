import networkx as nx

from csgo import NAV, NAV_GRAPHS
from scipy.spatial import distance

def point_in_area(map_name, area_id, point):
    """ Returns if the point is within an area id for a map.

    Args:
        map_name (string) : Map to search
        area_id (int)     : Area ID as an integer
        point (list)      : Point as a list (x,y,z)

    Returns:
        boolean : True if area contains the point, false if not
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if area_id not in NAV[map_name].keys():
        raise ValueError("Area ID not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    if (point[0] < NAV[map_name][area_id]["NorthWestX"]) and (point[0] > NAV[map_name][area_id]["SouthWestX"]) and (point[1] < NAV[map_name][area_id]["NorthWestY"]) and (point[1] > NAV[map_name][area_id]["SouthWestY"]) and (point[2] < NAV[map_name][area_id]["NorthWestZ"]) and (point[2] > NAV[map_name][area_id]["SouthWestZ"]):
        return True

def find_area(map_name, point):
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    for area in NAV[map_name].keys():
        if point_in_area(map_name, area, point):
            return NAV[map_name][area]
    return {"mapName": map_name, "areaID": None}

def area_distance(map_name, area_a, area_b, dist_type="graph"):
    """ Returns the distance between two areas.

    Args:
        map_name (string)  : Map to search
        area_a (int)       : Area id
        area_b (int)       : Area id
        dist_type (string) : String indicating the type of distance to use.
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if (area_a not in NAV[map_name].keys()) or (area_b not in NAV[map_name].keys()):
        raise ValueError("Area ID not found.")
    if dist_type in ["graph", "geodesic"]:
        raise ValueError("dist_type can only be graph or geodesic")
    G = NAV_GRAPHS[map_name]
    if dist_type == "graph":
        return len(nx.shortest_path(G, area_a, area_b))
    if dist_type == "geodesic":
        def dist(a, b):
            return G.nodes()[a]["Size"] + G.nodes()[b]["Size"]
        geodesic_path = nx.astar_path(G, area_a, area_b, heuristic=dist)
        geodesic_cost = 0
        for area in geodesic_path:
            geodesic_cost += G.nodes()[area]["Size"]
    return 0

def point_distance(map_name, point_a, point_b, dist_type="graph"):
    """ Returns the distance between two points.

    Args:
        map_name (string)  : Map to search
        point_a (list)     : Point as a list (x,y,z)
        point_b (list)     : Point as a list (x,y,z)
        dist_type (string) : String indicating the type of distance to use.
    """
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    
    if dist_type == "graph":
        area_a = find_area(map_name, point_a)["AreaId"]
        area_b = find_area(map_name, point_b)["AreaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "geodesic":
        area_a = find_area(map_name, point_a)["AreaId"]
        area_b = find_area(map_name, point_b)["AreaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "euclidean":
        return distance.euclidean(point_a, point_b)
    elif dist_type == "manhattan":
        return distance.cityblock(point_a, point_b)
    elif dist_type == "canberra":
        return distance.canberra(point_a, point_b)
    elif dist_type == "cosine":
        return distance.cosine(point_a, point_b)