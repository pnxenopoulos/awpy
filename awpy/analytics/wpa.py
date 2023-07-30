"""Will provide functionality for WPA and win probabilities.

WPA stands for Win Probability Added and is described in this paper:
https://arxiv.org/pdf/2011.01324.pdf.
"""
import json
from typing import Any

from awpy.types import GameFrame

SIMPLE_WP_MODEL = None
ADV_WP_MODEL = None


def state_win_probability(frame: GameFrame, model: Any) -> dict:  # noqa: ANN401
    """Predicts the win probability of a given frame.

    Args:
        frame (dict): Dict output of a frame generated from the DemoParser class
        model (Unknown): Model to predict win probabability from.

    Returns:
        A dictionary containing the CT and T round win probabilities
    """
    raise NotImplementedError


def round_win_probability(ct_score: int, t_score: int, map_name: str) -> dict:
    """Estimates of game win probability using information from the HLTV win matrix.

    Args:
        ct_score (int): CT Score
        t_score (int): T Score
        map_name (str): Map name the demo is from

    Returns:
        A dictionary containing the game win probability
    """
    # Load the data from the json file <-- will be moved to data _init_
    wpa_data = json.loads("../data/wpa/wpa.json")
    
    # Convert the keys back to integers
    wpa_data = {int(k): v for k, v in wpa_data.items()}
    
    # Get the map id from the map name
    map_id = _get_mapid(map_name)

    if map_id in wpa_data:
        map_data = wpa_data[map_id]

        # Get the win probabilities for the CT and T scores
        ct_win_prob = map_data["CT"].get(str(ct_score), {}).get(str(t_score))
        t_win_prob = map_data["TERRORIST"].get(str(t_score), {}).get(str(ct_score))

        # Check if the win probabilities were found
        if ct_win_prob is None:
            print(f"CT score {ct_score} not found in data for map {map_id}")

        if t_win_prob is None:
            print(f"T score {t_score} not found in data for map {map_id}")

        # Return the win probabilities
        return {"CT": ct_win_prob, "TERRORIST": t_win_prob}

    return {"Map ID not found in data": map_id}


def _get_mapid(map_name: str) -> int:
    """Helper to get the map_id from map_name.

    disabled for now "de_ancient": 47,

    Returns:
            int with the map_id

    """
    map_dict = {
        "de_cache": 29,
        "de_dust2": 31,
        "de_mirage": 32,
        "de_inferno": 33,
        "de_nuke": 34,
        "de_train": 35,
        "de_cbble": 39,
        "de_overpass": 40,
        "de_vertigo": 46,
        "de_anubis": 48,
    }

    if map_name in map_dict:
        return map_dict[map_name]
    raise ValueError
