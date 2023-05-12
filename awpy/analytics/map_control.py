from collections import defaultdict
import numpy as np

from awpy.data import NAV, NAV_GRAPHS
from awpy.analytics.nav import area_distance, find_closest_area, calculate_tile_area
from awpy.types import GameRound, GameFrame, TeamFrameInfo, FrameMapControl


def approx_neighbors(
    map_name: str,
    source_tile_id: int,
    n: int = 5,
) -> list[tuple[float, int]]:
    """Approximates neighbors for tiles by finding n closest. Helpful for
       tiles who are 'isolated' (they have no navigable tiles as a neighbor).
    Args:
        map_name (string)   : Map for source_tile_id
        source_tile_id (int): Area ID as an integer
        n (int)             : Number of closest tiles/approximated
                              neighbors wanted
    Returns:
        List of tuples representing n closest tiles.
            Tuple[0] -> Distance between source_tile_id and represented tile
            Tuple[1] -> Area ID of represented tile
    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If source_tile_id is not in awpy.data.NAV[map_name]
                    If the length of point is not 3
    """

    if map_name not in NAV:
        raise ValueError("Map not found.")
    if source_tile_id not in NAV[map_name].keys():
        raise ValueError("Area ID not found.")
    if n < 0:
        raise ValueError("n must be >= 0")

    currentMapInfo = NAV[map_name]
    distanceArr = []

    for tile in currentMapInfo:
        if tile != source_tile_id:
            currentDistance = area_distance(
                map_name, tile, source_tile_id, dist_type="euclidean"
            )["distance"]
            distanceArr.append((currentDistance, tile))
    distanceArr.sort()

    return distanceArr[:n]


def bfsHelper(
    map_name: str,
    current_tiles: list,
    neighbor_info: dict,
    estimate_neighbors: bool,
) -> dict:
    """Helper function to run bfs from each tile in current_tiles
    Args:
        map_name (string)        : Map for current_tiles
        current_tiles (list)     : List of tiles to use as start tile
                                   for bfs iteration(s)
        neighbor_info (dict)     : Dictionary
        estimate_neighbors (bool): Boolean whetheer neighbors should
                                   be estimated for isolated tiles
                                   (tiles with neighbors)
    Returns:
        Dictionary mapping tile id -> list of map control values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """

    """
    Should we use neighbors? Isolated tiles are then ignored
    
    Could use tile distance and iterate through closest n instead
    Tile Distance Ideas:
    1. Use neighbors - isolated tiles are ignored
    2. Use euclidean distance - could get incorrect 
    'neighboring' tiles in multi-floor maps?
    3. Combine graph and euclidean distance
        * If not isolated, use graph distance
        * If isolated
            * Find minimal graph distance to isolated tile
              * Track closest possible neighbor to isolated tile
            * Add euclidean distance to closest possible neighbor
              from isolated tile
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")

    currentDict = defaultdict(list)
    for curId in current_tiles:
        curId = int(curId)
        startVal = 10
        stepsize = 1
        tilesSeen = set()
        stack = []
        startingNode = (curId, startVal)
        stack.append(startingNode)
        while len(stack) > 0 and stack[0][1] > 0:
            curId, curVal = stack.pop(0)
            if curId not in tilesSeen:
                tilesSeen.add(curId)
                curTileValues = currentDict[curId]
                curTileValues.append(curVal / startVal)
                currentDict[curId] = curTileValues
                neighbors = neighbor_info[curId]
                if estimate_neighbors and len(neighbors) == 0:
                    neighbors = [
                        tileId for distance, tileId in approx_neighbors(map_name, curId)
                    ]
                for neighbor in neighbors:
                    stack.append((neighbor, curVal - stepsize))

    return currentDict


def frame_tile_map_control_values(
    map_name: str,
    ct_tiles_wanted: list[int],
    t_tiles_wanted: list[int],
    neighbor_info: dict,
    estimate_neighbors: bool = True,
) -> tuple[dict, dict]:
    """Calculate a frame's map control values for each side given
       a list of tiles habited by each side
    Args:
        map_name (string)        : Map for other arguments
        ct_tiles_wanted (list)   : List of tiles where ct players
                                   are located
        t_tiles_wanted (list)    : List of tiles where t players
                                   are located
        neighbor_info (dict)     : Dictionary
        estimate_neighbors (bool): Boolean whetheer neighbors should
                                   be estimated for isolated tiles
                                   (tiles with neighbors).
                                   Set to true as default.
    Returns:
        Tuple containing map control dictionary for each side
            Tuple[0] -> CT Dict
            Tuple[1] -> T Dict
    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """

    funcCTIds = [int(i) for i in list(ct_tiles_wanted)]
    funcTIds = [int(i) for i in list(t_tiles_wanted)]

    ### Run BFS For CT Tiles
    ctDict = bfsHelper(map_name, funcCTIds, neighbor_info, estimate_neighbors)

    ### Run BFS For T Tiles
    tDict = bfsHelper(map_name, funcTIds, neighbor_info, estimate_neighbors)

    return (ctDict, tDict)


def graphToEdgeDict(
    neighbor_pairs: list[tuple[int, int]],
) -> dict:
    """Given a list of neighboring tiles, return a dictionary
       mapping a tile id to a set containing its neighboring tiles'
       ids
    Args:
        inputGraphEdges (list[...])  : List of tuples (pairs of
                                       neighboring tiles)
    Returns: Dictionary that maps a tile to a set of neighboring tiles
    """

    returnDict = defaultdict(set)

    for currentEdge1, currentEdge2 in neighbor_pairs:
        if currentEdge2 not in returnDict[currentEdge1]:
            returnDict[currentEdge1].add(currentEdge2)
        if currentEdge1 not in returnDict[currentEdge2]:
            returnDict[currentEdge2].add(currentEdge1)
    return returnDict


def calcMapControlHelper(
    map_name: str,
    current_player_data: dict,
    approx_neighbors: bool = True,
) -> FrameMapControl:
    """Helper function to calculate tile map control values for each team
    Args:
        map_name (string)            : Map used for find_closest_area and
                                       and relevant tile neighbor dictionary
        current_player_data (dict)   : Dictionary
        estimate_neighbors (boolean) : Boolean whether neighbors should
                                       be estimated for isolated tiles
                                       (tiles with neighbors).
                                       Set to true as default.
    Returns: Dictionary for each team's map control values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If current_player_data not of expected
                    awpy frame format
    """

    if map_name not in NAV:
        raise ValueError("Map not found.")
    if "t" not in current_player_data or "ct" not in current_player_data:
        raise ValueError("Player data dictionary not of expected awpy frame formatting")

    tLocs = current_player_data["t"]["player-locations"]
    ctLocs = current_player_data["ct"]["player-locations"]

    """
    Would be nice to remove below tile queries or find a way around this long term 
    if function is used in demo parsing script long term
    """

    currentMapGraphNeighborDict = graphToEdgeDict(
        NAV_GRAPHS[map_name].edges
    )  # graphDicts[map_name]

    ### Largest time block is find_closest_area:
    ### 75% of function's time is in the function call
    tTiles = [find_closest_area(map_name, i)["areaId"] for i in tLocs]
    ctTiles = [find_closest_area(map_name, i)["areaId"] for i in ctLocs]

    ctVals, tVals = frame_tile_map_control_values(
        map_name, ctTiles, tTiles, currentMapGraphNeighborDict, approx_neighbors
    )

    return {"ct": ctVals, "t": tVals}


def calcMapControl(
    map_name: str,
    frame: GameFrame,
    approx_neighbors: bool = True,
) -> FrameMapControl:
    """Calculate tile map control values for each team given frame object
    Args:
        map_name (string)            : Map used for find_closest_area and
                                       and relevant tile neighbor dictionary
        frame (GameFrame)            : Awpy frame object for map control
                                       calculations
        estimate_neighbors (boolean) : Boolean whetheer neighbors should
                                       be estimated for isolated tiles
                                       (tiles with neighbors).
                                       Set to true as default.
    Returns: Dictionary for each team's map control values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If current_player_data not of expected
                    awpy frame format
    """

    if map_name not in NAV:
        raise ValueError("Map not found.")

    parsedData = parseRoundFrame(frame)

    return calcMapControlHelper(
        map_name=map_name,
        current_player_data=parsedData,
        approx_neighbors=approx_neighbors,
    )


def parseRoundFrameHelper(
    side_data: TeamFrameInfo,
) -> list[list[float]]:
    """Helper function to parse player locations for
        alive players in given side_data
    Args:
        side_data (TeamFrameInfo)       : Dict holding data for sides' players.
                                          Expects frame['t'] or frame['ct'] to
                                          be passed in.
    Returns: List of player locations

    Raises:
        ValueError: If side_data not of expected awpy frame['t'] or
                    frame['ct']

    """
    if "players" not in side_data:
        raise ValueError(
            "side_data variable not of expected awpy frame['t'] or frame['ct'] format."
        )

    coords = ["x", "y", "z"]
    returnList = []

    for player in side_data["players"]:
        if player["isAlive"]:
            curPlayerLocation = [player[dim] for dim in coords]
            returnList.append(curPlayerLocation)
    return returnList


def parseRoundFrame(
    frame: GameFrame,
) -> dict:
    """Parse frame data for alive player locations for
       both sides and return data in a dictionary
    Args:
        frame (dict)       : Dictionary in the form of an awpy frame
                             containing relevant data for both sides
    Returns: Dictionary containing player locations for both sides
             for the current frame

    Raises:
        ValueError: If current_player_data not of expected
                    awpy frame format
                    If no players are alive for both sides
    """

    if "t" not in frame or "ct" not in frame:
        raise ValueError("frame variable not of expected awpy frame format.")

    returnDict = {}
    returnDict["t"] = {"player-locations": parseRoundFrameHelper(frame["t"])}
    returnDict["ct"] = {"player-locations": parseRoundFrameHelper(frame["ct"])}
    if len(returnDict["t"]['player-locations']) == 0 and len(returnDict["ct"]['player-locations']) == 0:
        raise ValueError("No alive players on either team for given frame")
    return returnDict

def map_control_metric_helper(
    map_name: str,
    mc_values: FrameMapControl,
) -> float:
    """Return map control metric given map control dictionary
        containing values for both teams (output of calcMapControl)
    Args:
        map_name (string)               : Map used in calculate_tile_area
        mc_values (FrameMapControl)     : FrameMapControl object containing map control
                                          values for both teams. Expected
                                          format that of calcMapControl output

    Returns: Map Control Metric given dictionary of values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If mc_values is not in expected format
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if mc_values and ("ct" not in mc_values or "t" not in mc_values):
        raise ValueError("Map Control dictionary not in expected format.")

    current_map_control_value = []
    tileAreas = []
    for tile in set(list(mc_values["ct"].keys()) + list(mc_values["t"].keys())):
        ctValue, tValue = mc_values["ct"][tile], mc_values["t"][tile]

        current_map_control_value.append(sum(ctValue) / (sum(ctValue) + sum(tValue)))
        tileAreas.append(calculate_tile_area(map_name, int(tile)))

    current_map_control_value = np.array(current_map_control_value)
    tileAreas = np.array(tileAreas)

    return sum(current_map_control_value * tileAreas) / sum(tileAreas)


def frame_map_control_metric(
    map_name: str,
    frame: GameFrame,
) -> float:
    """Return map control metric for given awpy frame
    Args:
        map_name (string)       : Map used position_transform call
        frame (GameFrame)       : awpy frame to calculate map
                                  control metric for

    Returns: Map Control metric for given frame

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")

    mapControlDict = calcMapControl(map_name, frame, True)
    return map_control_metric_helper(map_name, mapControlDict)


def calculate_round_map_control_metrics(
    map_name: str,
    round_data: GameRound,
) -> list[float]:
    """Return list of map control metric for given awpy round
    Args:
        map_name (string)       : Map used position_transform call
        round_data (dict)       : awpy round to calculate map
                                  control metrics for

    Returns: List of map control metric values for given round

    Raises:
        ValueError: If round_data is not in awpy round format
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if "frames" not in round_data:
        raise ValueError("Round data not in expected round formatn.")

    mapControlMetricTracker = []
    for frame in round_data["frames"]:
        currentMCMetric = frame_map_control_metric(map_name, frame)
        mapControlMetricTracker.append(currentMCMetric)
    return mapControlMetricTracker
