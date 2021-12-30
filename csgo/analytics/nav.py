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
    if (point[0] > NAV[map_name][area_id]["NorthWestX"]) and (point[0] < NAV[map_name][area_id]["SouthEastX"]) and (point[1] < NAV[map_name][area_id]["NorthWestY"]) and (point[1] > NAV[map_name][area_id]["SouthEastY"]) and (point[2] > NAV[map_name][area_id]["NorthWestZ"]) and (point[2] < NAV[map_name][area_id]["SouthEastZ"]):
        return True

def find_area(map_name, point):
    if map_name not in NAV.keys():
        raise ValueError("Map not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    for area in NAV[map_name].keys():
        if point_in_area(map_name, area, point):
            nav_to_return = NAV[map_name][area]
            nav_to_return["MapName"] = map_name
            nav_to_return["AreaId"] = area
            return nav_to_return
    return {"MapName": map_name, "AreaId": None}

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
    if dist_type not in ["graph", "geodesic"]:
        raise ValueError("dist_type can only be graph or geodesic")
    G = NAV_GRAPHS[map_name]
    if dist_type == "graph":
        return len(nx.shortest_path(G, area_a, area_b))-1
    if dist_type == "geodesic":
        def dist(a, b):
            return G.nodes()[a]["Size"] + G.nodes()[b]["Size"]
        geodesic_path = nx.astar_path(G, area_a, area_b, heuristic=dist)
        geodesic_cost = 0
        for i, area in enumerate(geodesic_path):
            if i > 0:
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
    
    
    if dist_type == "graph":
        if map_name not in NAV.keys():
            raise ValueError("Map not found.")
        if len(point_a) != 3 or len(point_b) != 3:
            raise ValueError("When using graph or geodesic distance, point must be X/Y/Z")
        area_a = find_area(map_name, point_a)["AreaId"]
        area_b = find_area(map_name, point_b)["AreaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "geodesic":
        if map_name not in NAV.keys():
            raise ValueError("Map not found.")
        if len(point_a) != 3 or len(point_b) != 3:
            raise ValueError("When using graph or geodesic distance, point must be X/Y/Z")
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

class PlaceEncoder:
    """Encodes map and places"""

    def __init__(self):
        self.places = [
            "TSpawn",
            "Dumpster",
            "Fountain",
            "Roof",
            "ElectricalBox",
            "Shop",
            "Heaven",
            "Arch",
            "OutsideTunnel",
            "Deck",
            "Vending",
            "BombsiteB",
            "TRamp",
            "BPlatform",
            "TCorridorUp",
            "ExtendedA",
            "Admin",
            "StorageRoom",
            "Garage",
            "TMain",
            "Mini",
            "LowerPark",
            "Outside",
            "Restroom",
            "UnderA",
            "Tunnel1",
            "BackofB",
            "LongA",
            "Graveyard",
            "Secret",
            "Lobby",
            "LowerMid",
            "Silo",
            "PopDog",
            "Ivy",
            "Hole",
            "SecondMid",
            "LadderTop",
            "Playground",
            "Hell",
            "TopofMid",
            "Window",
            "OutsideLong",
            "Control",
            "Walkway",
            "CTSpawn",
            "Kitchen",
            "TicketBooth",
            "Ramp",
            "Scaffolding",
            "HutRoof",
            "Alley",
            "BackDoor",
            "BombsiteA",
            "Catwalk",
            "Apartments",
            "Jungle",
            "UpperTunnel",
            "Tunnel2",
            "Connector",
            "BDoors",
            "TStairs",
            "LowerTunnel",
            "Hut",
            "Truck",
            "Tunnel",
            "PalaceInterior",
            "LadderBottom",
            "Upstairs",
            "Decon",
            "Side",
            "Library",
            "Elevator",
            "MidDoors",
            "UpperPark",
            "Vents",
            "Middle",
            "Mid",
            "ShortStairs",
            "Ruins",
            "Trophy",
            "SideAlley",
            "Squeaky",
            "Quad",
            "LockerRoom",
            "Construction",
            "Water",
            "BackofA",
            "SnipersNest",
            "Rafters",
            "Pit",
            "Short",
            "Bridge",
            "Underpass",
            "Tunnels",
            "ARamp",
            "Banana",
            "Stairs",
            "Canal",
            "APlatform",
            "Pipe",
            "TunnelStairs",
            "LongDoors",
            "House",
            "Observation",
            "Crane",
            "Balcony",
            "Ladder",
            "BackAlley",
            "PalaceAlley",
        ]
        self.places_len = len(self.places)
        self.maps = [
            "de_dust2",
            "de_mirage",
            "de_inferno",
            "de_nuke",
            "de_train",
            "de_overpass",
            "de_vertigo",
        ]
        self.maps_len = len(self.maps)

    def encode(self, type, item):
        if type == "place":
            output = [0 for i in range(self.places_len)]
        elif type == "map":
            output = [0 for i in range(self.maps_len)]
        else:
            output = [0 for i in range(self.places_len)]
        try:
            if type == "place":
                obj_idx = self.places.index(item)
            elif type == "map":
                obj_idx = self.maps.index(item)
            else:
                obj_idx = self.places.index(item)
            output[obj_idx] = 1
        except ValueError:
            pass
        return output
