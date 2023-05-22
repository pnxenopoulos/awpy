"""Functions for calculating map control values and metrics.

    A team's map control can be thought of as the sum of it's
    individual player's control.

    Example notebook:

    github.com/pnxenopoulos/awpy/blob/main/examples/05_Map_Control_Calculations_And_Visualizations.ipynb
"""

from collections import defaultdict, deque

import numpy as np

from awpy.analytics.nav import area_distance, calculate_tile_area, find_closest_area
from awpy.data import NAV, NAV_GRAPHS
from awpy.types import (
    BFSTileData,
    FrameMapControlValues,
    FrameTeamMetadataDict,
    FrameTeamMetadataObject,
    GameFrame,
    GameRound,
    TeamFrameInfo,
    TeamMapControlValuesDict,
    TileDistanceObject,
    TileIdObject,
    TileNeighborsDict,
)


def _approx_neighbors(
    map_name: str,
    source_tile_id: TileIdObject,
    n_neighbors: int = 5,
) -> list[TileDistanceObject]:
    """Approximates neighbors for isolated tiles by finding n closest tiles.

    Args:
        map_name (str): Map for source_tile_id
        source_tile_id (TileIdObject): TileIdObject for source tile
        n_neighbors (int): Number of closest tiles/approximated neighbors wanted

    Returns:
        List of TileDistanceObjects for n closest tiles

    Raises:
        ValueError: If source_tile_id is not in awpy.data.NAV[map_name]
                    If n_neighbors <= 0
    """
    if source_tile_id not in NAV[map_name].keys():
        msg = "Area ID not found."
        raise ValueError(msg)
    if n_neighbors <= 0:
        msg = "Invalid n_neighbors value. Must be > 0"
        raise ValueError(msg)

    current_map_info = NAV[map_name]
    possible_neighbors_arr: list[TileDistanceObject] = []

    for tile in current_map_info:
        if tile != source_tile_id:
            # TODO: See if AREA_DIST_MATRIX is worth incorporating
            current_distance = area_distance(
                map_name, tile, source_tile_id, dist_type="euclidean"
            )["distance"]
            current_tile_id = TileIdObject(tile)
            current_tile_distance_obj: TileDistanceObject = {
                "distance": current_distance,
                "tile_id": current_tile_id,
            }
            possible_neighbors_arr.append(current_tile_distance_obj)

    sorted_neighbors = sorted(possible_neighbors_arr, key=lambda d: d["distance"])

    return sorted_neighbors[:n_neighbors]


def _bfs_helper(
    map_name: str,
    current_tiles: list[TileIdObject],
    neighbor_info: TileNeighborsDict,
    max_depth: int = 10,
) -> TeamMapControlValuesDict:
    """Helper function to run bfs from given tiles to generate map_control values dict.

    Args:
        map_name (str): Map for current_tiles
        current_tiles (TileIdObject): List of source tiles for bfs iteration(s)
        neighbor_info (dict): Dictionary mapping tile to its navigable neighbors
        max_depth (int): Max tile distance from source tile to be considered

    Returns:
        TeamMapControlValuesDict containing map control values

    Raises:
        ValueError: If max_depth <= 0

    Values are allocated to tiles depending on how many tiles are between it
    and the source tile (aka tile distance). The smaller the tile distance,
    the close the tile's value is to 1. The tile distance can get as high as
    the max_depth argument, which is 10 as default. If the max_depth is kept
    as default 10, this means the BFS search will stop once a tile
    distance of 10 is reached.
    """
    if max_depth <= 0:
        msg = "Invalid max_depth value. Must be > 0."
        raise ValueError(msg)

    map_control_values = TeamMapControlValuesDict(defaultdict(list))
    for cur_start_tile in current_tiles:
        tiles_seen: set[TileIdObject] = set()

        start_tile: BFSTileData = {
            "tile_id": cur_start_tile,
            "map_control_value": 1.0,
            "steps_left": max_depth,
        }

        queue: deque[BFSTileData] = deque([start_tile])

        while queue and queue[0]["steps_left"] > 0:
            cur_tile = queue.popleft()
            cur_id = cur_tile["tile_id"]
            if cur_id not in tiles_seen:
                tiles_seen.add(cur_id)
                map_control_values[cur_id].append(cur_tile["map_control_value"])

                neighbors = [TileIdObject(i) for i in neighbor_info[cur_id]]
                if len(neighbors) == 0:
                    neighbors = [
                        tile["tile_id"] for tile in _approx_neighbors(map_name, cur_id)
                    ]

                queue.extend(
                    [
                        BFSTileData(
                            {
                                "tile_id": neighbor,
                                "map_control_value": (cur_tile["steps_left"] - 1)
                                / max_depth,
                                "steps_left": cur_tile["steps_left"] - 1,
                            }
                        )
                        for neighbor in neighbors
                    ]
                )

    return map_control_values


def _frame_tile_map_control_values(
    map_name: str,
    ct_tiles: list[TileIdObject],
    t_tiles: list[TileIdObject],
    neighbor_info: TileNeighborsDict,
) -> FrameMapControlValues:
    """Calculate a frame's map control values for each side.

    Args:
        map_name (str): Map for other arguments
        ct_tiles (list): List of CT-occupied tiles
        t_tiles (list): List of T-occupied tiles
        neighbor_info (TileNeighborsDict): Object with tile to neighbor mapping

    Returns:
        FrameMapControlValues object containing each team's map control values

    Values are allocated to tiles depending on how many tiles are between it
    and the source tile (aka tile distance). The smaller the tile distance,
    the close the tile's value is to 1. The tile distance can get as high as
    the max_depth argument, which is 10 as default. If the max_depth is kept
    as default 10, this means the BFS search will stop once a tile
    distance of 10 is reached.
    """
    # Run BFS For CT Tiles
    ct_values = _bfs_helper(map_name, ct_tiles, neighbor_info)

    # Run BFS For T Tiles
    t_values = _bfs_helper(map_name, t_tiles, neighbor_info)

    frame_map_control: FrameMapControlValues = {
        "ct": ct_values,
        "t": t_values,
    }

    return frame_map_control


def graph_to_tile_neighbors(
    neighbor_pairs: list[tuple[TileIdObject, TileIdObject]],
) -> TileNeighborsDict:
    """Convert list of neighboring tiles to TileNeighborsDict object.

    Args:
        neighbor_pairs (list): List of tuples (pairs of TileIdObject)

    Returns: TileNeighborsDict object with tile to neighbor mapping
    """
    tile_to_neighbors = TileNeighborsDict(defaultdict(set))

    for tile_1, tile_2 in neighbor_pairs:
        tile_to_neighbors[tile_1].add(tile_2)
        tile_to_neighbors[tile_2].add(tile_1)

    return tile_to_neighbors


def calc_parsed_frame_map_control_values(
    map_name: str,
    current_player_data: FrameTeamMetadataObject,
) -> FrameMapControlValues:
    """Calculate tile map control values for each team given parsed frame.

    Args:
        map_name (str): Map used for find_closest_area and
                        relevant tile neighbor dictionary
        current_player_data (FrameTeamMetadataObject): Object containing team metadata
                                                       (player positions, etc.)
                                                       Expects extract_player_positions
                                                       output format

    Returns: FrameMapControlValues object containing each team's map control values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV

    Values are allocated to tiles depending on how many tiles are between it
    and the source tile (aka tile distance). The smaller the tile distance,
    the close the tile's value is to 1. The tile distance can get as high as
    the max_depth argument, which is 10 as default. If the max_depth is kept
    as default 10, this means the BFS search will stop once a tile
    distance of 10 is reached.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    t_locations = current_player_data["t"]["alive_player_locations"]
    ct_locations = current_player_data["ct"]["alive_player_locations"]

    neighboring_tiles = list(NAV_GRAPHS[map_name].edges)

    neighboring_tile_id_objs = [
        (TileIdObject(i), TileIdObject(j)) for i, j in neighboring_tiles
    ]

    neighbors_dict = graph_to_tile_neighbors(neighboring_tile_id_objs)

    t_tiles = [
        TileIdObject(find_closest_area(map_name, i)["areaId"]) for i in t_locations
    ]
    ct_tiles = [
        TileIdObject(find_closest_area(map_name, i)["areaId"]) for i in ct_locations
    ]

    return _frame_tile_map_control_values(map_name, ct_tiles, t_tiles, neighbors_dict)


def calc_frame_map_control_values(
    map_name: str,
    frame: GameFrame,
) -> FrameMapControlValues:
    """Calculate tile map control values for each team given frame object.

    Args:
        map_name (str): Map used for find_closest_area and
            relevant tile neighbor dictionary
        frame (GameFrame): Awpy frame object for map control calculations

    Returns: FrameMapControlValues object containing each team's map control values

    Raises:
        ValueError: If map_name is not in awpy.data.NAV

    Values are allocated to tiles depending on how many tiles are between it
    and the source tile (aka tile distance). The smaller the tile distance,
    the close the tile's value is to 1. The tile distance can get as high as
    the max_depth argument, which is 10 as default. If the max_depth is kept
    as default 10, this means the BFS search will stop once a tile
    distance of 10 is reached.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    return calc_parsed_frame_map_control_values(
        map_name=map_name,
        current_player_data=extract_teams_metadata(frame),
    )


def _extract_team_metadata_helper(
    side_data: TeamFrameInfo,
) -> FrameTeamMetadataDict:
    """Helper function to parse player locations in given side_data.

    Args:
        side_data (TeamFrameInfo): Object with metadata for side's players.

    Returns: FrameTeamMetadataDict with metadata on team's players
    """
    coords = ("x", "y", "z")
    alive_players: list[list[float]] | list = [
        [player[dim] for dim in coords]
        for player in side_data["players"] or []
        if player["isAlive"]
    ]

    return FrameTeamMetadataDict({"alive_player_locations": alive_players})


def extract_teams_metadata(
    frame: GameFrame,
) -> FrameTeamMetadataObject:
    """Parse frame data for alive player locations for both sides.

    Args:
        frame (GameFrame): Dictionary in the form of an awpy frame
                           containing relevant data for both sides

    Returns: FrameTeamMetadataObject containing team metadata (player
             positions, etc.)

    Raises:
        ValueError: If no players are alive for both sides
    """
    teams_metadata: FrameTeamMetadataObject = {
        "t": _extract_team_metadata_helper(frame["t"]),
        "ct": _extract_team_metadata_helper(frame["ct"]),
    }

    return teams_metadata


def _map_control_metric_helper(
    map_name: str,
    mc_values: FrameMapControlValues,
) -> float:
    """Return map control metric given FrameMapControlValues object.

    Args:
        map_name (str): Map used in calculate_tile_area
        mc_values (FrameMapControlValues): FrameMapControlValues object
                                           containing map control values
                                           for both teams.
                                           Expected format that of
                                           calc_frame_map_control_values output

    Returns: Map Control Metric given dictionary of values

    Raises:
        ValueError: If mc_values is not in expected format

    Map Control metric is used to quantify how much of the map is controlled
    by T/CT. Each tile is given a value between 0 (complete T control) and 1
    (complete CT control). If a tile is controlled by both teams, a value is
    found by taking the ratio between the sum of CT values and sum of CT and
    T values. Once all of the tiles' values are calculated, a weighted sum
    is done on the tiles' values where the tiles' area is the weights.
    This weighted sum is the map control metric returned at the end of the function.
    """
    current_map_control_value: list[float] = []
    tile_areas: list[float] = []
    for tile in set(mc_values["ct"].keys() | set(mc_values["t"].keys())):
        ct_val, t_val = mc_values["ct"][tile], mc_values["t"][tile]

        current_map_control_value.append(sum(ct_val) / (sum(ct_val) + sum(t_val)))
        tile_areas.append(calculate_tile_area(map_name, int(tile)))

    np_current_map_control_value = np.array(current_map_control_value)
    np_tile_areas = np.array(tile_areas)

    return sum(np_current_map_control_value * np_tile_areas) / sum(np_tile_areas)


def calc_frame_map_control_metric(
    map_name: str,
    frame: GameFrame,
) -> float:
    """Return map control metric for given awpy frame.

    Args:
        map_name (str): Map used position_transform call
        frame (GameFrame): awpy frame to calculate map control metric for

    Returns: Map Control metric for given frame

    Raises:
        ValueError: If map_name is not in awpy.data.NAV

    Map Control metric is used to quantify how much of the map is controlled
    by T/CT. Each tile is given a value between 0 (complete T control) and 1
    (complete CT control). If a tile is controlled by both teams, a value is
    found by taking the ratio between the sum of CT values and sum of CT and
    T values. Once all of the tiles' values are calculated, a weighted sum
    is done on the tiles' values where the tiles' area is the weights.
    This weighted sum is the map control metric returned at the end of the function.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    map_control_values = calc_frame_map_control_values(map_name, frame)
    return _map_control_metric_helper(map_name, map_control_values)


def calculate_round_map_control_metrics(
    map_name: str,
    round_data: GameRound,
) -> list[float]:
    """Return list of map control metric for given awpy round.

    Args:
        map_name (str): Map used position_transform call
        round_data (GameRound): awpy round to calculate map control metrics for

    Returns: List of map control metric values for given round

    Raises:
        ValueError: If map_name is not in awpy.data.NAV

    Map Control metric is used to quantify how much of the map is controlled
    by T/CT. Each tile is given a value between 0 (complete T control) and 1
    (complete CT control). If a tile is controlled by both teams, a value is
    found by taking the ratio between the sum of CT values and sum of CT and
    T values. Once all of the tiles' values are calculated, a weighted sum
    is done on the tiles' values where the tiles' area is the weights.
    This weighted sum is the map control metric returned at the end of the function.
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    map_control_metrics: list[float] = []
    for frame in round_data["frames"] or []:
        current_frame_metric = calc_frame_map_control_metric(map_name, frame)
        map_control_metrics.append(current_frame_metric)
    return map_control_metrics
