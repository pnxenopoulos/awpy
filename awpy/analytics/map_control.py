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

    current_map_info = NAV[map_name]
    distance_arr: list[float] = []

    for tile in current_map_info:
        if tile != source_tile_id:
            current_distance = area_distance(
                map_name, tile, source_tile_id, dist_type="euclidean"
            )["distance"]
            distance_arr.append((current_distance, tile))
    distance_arr.sort()

    return distance_arr[:n]


def bfs_helper(
    map_name: str,
    current_tiles: list[int],
    neighbor_info: dict[int, list[int]],
    estimate_neighbors: bool,
) -> dict:
    """Helper function to run bfs from each tile in current_tiles

    Args:
        map_name (string)        : Map for current_tiles
        current_tiles (list)     : List of tiles to use as start tile
                                   for bfs iteration(s)
        neighbor_info (dict)     : Dictionary mapping tile to its
                                   navigable neighbors
        estimate_neighbors (bool): Boolean whetheer neighbors should
                                   be estimated for isolated tiles
                                   (tiles with neighbors)
    Returns:
        Dictionary mapping tile id -> list of map control values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """

    if map_name not in NAV:
        raise ValueError("Map not found.")

    current_dict = defaultdict(list)
    for cur_id in current_tiles:
        cur_id = int(cur_id)
        start_val = 10
        step_size = 1
        tiles_seen = set()
        stack: list[tuple[int, int]] = []
        starting_node = (cur_id, start_val)
        stack.append(starting_node)
        while len(stack) > 0 and stack[0][1] > 0:
            cur_id, curVal = stack.pop(0)
            if cur_id not in tiles_seen:
                tiles_seen.add(cur_id)
                cur_tile_values = current_dict[cur_id]
                cur_tile_values.append(curVal / start_val)
                current_dict[cur_id] = cur_tile_values
                neighbors = neighbor_info[cur_id]
                if estimate_neighbors and len(neighbors) == 0:
                    neighbors = [tile_id for _, tile_id in approx_neighbors(map_name, cur_id)]
                for neighbor in neighbors:
                    stack.append((neighbor, curVal - step_size))

    return current_dict


def frame_tile_map_control_values(
    map_name: str,
    ct_tiles_wanted: list[int],
    t_tiles_wanted: list[int],
    neighbor_info: dict[int, list[int]],
    estimate_neighbors: bool = True,
) -> tuple[dict[int, list[float]], dict[int, list[float]]]:
    """Calculate a frame's map control values for each side given
       a list of tiles habited by each side

    Args:
        map_name (string)        : Map for other arguments
        ct_tiles_wanted (list)   : List of tiles where ct players
                                   are located
        t_tiles_wanted (list)    : List of tiles where t players
                                   are located
        neighbor_info (dict)     : Dictionary mapping tile to its
                                   navigable neighbors
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

    ct_tiles = [int(i) for i in list(ct_tiles_wanted)]
    t_tiles = [int(i) for i in list(t_tiles_wanted)]

    # Run BFS For CT Tiles
    ct_dict = bfs_helper(map_name, ct_tiles, neighbor_info, estimate_neighbors)

    # Run BFS For T Tiles
    t_dict = bfs_helper(map_name, t_tiles, neighbor_info, estimate_neighbors)

    return (ct_dict, t_dict)


def graph_to_tile_neighbors(
    neighbor_pairs: list[tuple[int, int]],
) -> dict[int, set[int]]:
    """Given a list of neighboring tiles, return a dictionary
       mapping a tile id to a set containing its neighboring tiles'
       ids

    Args:
        neighbor_pairs (list[...])  : List of tuples (pairs of
                                       neighboring tiles)
    Returns: Dictionary that maps a tile to a set of neighboring tiles
    """

    tile_to_neighbors = defaultdict(set)

    for tile_1, tile_2 in neighbor_pairs:
        if tile_2 not in tile_to_neighbors[tile_1]:
            tile_to_neighbors[tile_1].add(tile_2)
        if tile_1 not in tile_to_neighbors[tile_2]:
            tile_to_neighbors[tile_2].add(tile_1)
    return tile_to_neighbors


def _calc_map_control_helper(
    map_name: str,
    current_player_data: dict,
    approx_neighbors: bool = True,
) -> FrameMapControl:
    """Helper function to calculate tile map control values for each team

    Args:
        map_name (string)            : Map used for find_closest_area and
                                       and relevant tile neighbor dictionary
        current_player_data (dict)   : Dictionary containing alive player
                                       locations. Expects extract_player_positions
                                       output format
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

    t_locations = current_player_data["t"]["player-locations"]
    ct_locations = current_player_data["ct"]["player-locations"]

    neighbors_dict = graph_to_tile_neighbors(
        NAV_GRAPHS[map_name].edges
    ) 

    t_tiles = [find_closest_area(map_name, i)["areaId"] for i in t_locations]
    ct_tiles = [find_closest_area(map_name, i)["areaId"] for i in ct_locations]

    ct_values, t_values = frame_tile_map_control_values(
        map_name, ct_tiles, t_tiles, neighbors_dict, approx_neighbors
    )

    frame_map_control: FrameMapControl = {
        "ct": ct_values,
        "t": t_values,
    }

    return frame_map_control


def calc_map_control(
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

    player_positions = extract_player_positions(frame)

    return _calc_map_control_helper(
        map_name=map_name,
        current_player_data=player_positions,
        approx_neighbors=approx_neighbors,
    )


def _extract_player_positions_helper(
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
    alive_players: list[list[float]] = []

    for player in side_data["players"]:
        if player["isAlive"]:
            alive_players.append([player[dim] for dim in coords])
    return alive_players


def extract_player_positions(
    frame: GameFrame,
) -> dict[str, dict[str, list[list[float]]]]:
    """Parse frame data for alive player locations for
       both sides and return data in a dictionary

    Args:
        frame (GameFrame)  : Dictionary in the form of an awpy frame
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

    return_dict: dict[str, dict[str, list[list[float]]]] = {}
    return_dict["t"] = {"player-locations": _extract_player_positions_helper(frame["t"])}
    return_dict["ct"] = {"player-locations": _extract_player_positions_helper(frame["ct"])}
    if len(return_dict["t"]['player-locations']) == 0 and len(return_dict["ct"]['player-locations']) == 0:
        raise ValueError("No alive players on either team for given frame")
    return return_dict

def _map_control_metric_helper(
    map_name: str,
    mc_values: FrameMapControl,
) -> float:
    """Return map control metric given map control dictionary
       containing values for both teams (output of calc_map_control)

    Args:
        map_name (string)               : Map used in calculate_tile_area
        mc_values (FrameMapControl)     : FrameMapControl object containing map control
                                          values for both teams. Expected
                                          format that of calc_map_control output

    Returns: Map Control Metric given dictionary of values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If mc_values is not in expected format
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if mc_values and ("ct" not in mc_values or "t" not in mc_values):
        raise ValueError("Map Control dictionary not in expected format.")

    current_map_control_value: list[float] = []
    tile_areas: list[float] = []
    for tile in set(list(mc_values["ct"].keys()) + list(mc_values["t"].keys())):
        ct_val, t_val = mc_values["ct"][tile], mc_values["t"][tile]

        current_map_control_value.append(sum(ct_val) / (sum(ct_val) + sum(t_val)))
        tile_areas.append(calculate_tile_area(map_name, int(tile)))

    current_map_control_value = np.array(current_map_control_value)
    tile_areas = np.array(tile_areas)

    return sum(current_map_control_value * tile_areas) / sum(tile_areas)


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

    map_control_values = calc_map_control(map_name, frame, True)
    return _map_control_metric_helper(map_name, map_control_values)


def calculate_round_map_control_metrics(
    map_name: str,
    round_data: GameRound,
) -> list[float]:
    """Return list of map control metric for given awpy round

    Args:
        map_name (string)       : Map used position_transform call
        round_data (GameRound)  : awpy round to calculate map
                                  control metrics for

    Returns: List of map control metric values for given round

    Raises:
        ValueError: If round_data is not in awpy round format
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if "frames" not in round_data:
        raise ValueError("Round data not in expected round format.")

    map_control_metrics: list[float] = []
    for frame in round_data["frames"]:
        current_frame_metric = frame_map_control_metric(map_name, frame)
        map_control_metrics.append(current_frame_metric)
    return map_control_metrics
