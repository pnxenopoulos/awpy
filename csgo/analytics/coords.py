""" Coordinate conversion functions for csgo
"""

import os
import subprocess
import numpy as np

class PlaceEncode:
    """ Encodes map value into a one-hot encoded string
    """
    def __init__(self):
        self.places = ['TSpawn', 'Dumpster', 'Fountain', 'Roof', 'ElectricalBox', 'Shop', 'Heaven', 'Arch', 'OutsideTunnel', 'Deck', 'Vending', 'BombsiteB', 'TRamp', 'BPlatform', 'TCorridorUp', 'ExtendedA', 'Admin', 'StorageRoom', 'Garage', 'TMain', 'Mini', 'LowerPark', 'Outside', 'Restroom', 'UnderA', 'Tunnel1', 'BackofB', 'LongA', 'Graveyard', 'Secret', 'Lobby', 'LowerMid', 'Silo', 'PopDog', 'Ivy', 'Hole', 'SecondMid', 'LadderTop', 'Playground', 'Hell', 'TopofMid', 'Window', 'OutsideLong', 'Control', 'Walkway', 'CTSpawn', 'Kitchen', 'TicketBooth', 'Ramp', 'Scaffolding', 'HutRoof', 'Alley', 'BackDoor', 'BombsiteA', 'Catwalk', 'Apartments', 'Jungle', 'UpperTunnel', 'Tunnel2', 'Connector', 'BDoors', 'TStairs', 'LowerTunnel', 'Hut', 'Truck', 'Tunnel', 'PalaceInterior', 'LadderBottom', 'Upstairs', 'Decon', 'Side', 'Library', 'Elevator', 'MidDoors', 'UpperPark', 'Vents', 'Middle', 'Mid', 'ShortStairs', 'Ruins', 'Trophy', 'SideAlley', 'Squeaky', 'Quad', 'LockerRoom', 'Construction', 'Water', 'BackofA', 'SnipersNest', 'Rafters', 'Pit', 'Short', 'Bridge', 'Underpass', 'Tunnels', 'ARamp', 'Banana', 'Stairs', 'Canal', 'APlatform', 'Pipe', 'TunnelStairs', 'LongDoors', 'House', 'Observation', 'Crane', 'Balcony', 'Ladder', 'BackAlley', 'PalaceAlley']
        self.places_len = len(self.places)
    def encode(self, place_name):
        """ Encodes name to OHE.
        Arguments:
            place_name (string) : Place name to encode
        """
        output = [0 for i in range(self.places_len)]
        try:
            output[self.places.index(place_name)] = 1
        except ValueError:
            pass
        return output

def coords_to_area(x=0, y=0, z=0, map="de_dust2"):
    """Returns a dicitonary of the area

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