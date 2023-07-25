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
    # Load the data from the json file
    wpa_data = json.loads("../data/wpa/wpa.json")

    # Get the map id from the map name
    map_id = _get_mapid(map_name)

    # Determine the team based on the scores
    team = "CT" if ct_score > t_score else "TERRORIST"

    # If the map_id, team, ct_score, or t_score is not in the data, return
    if (
        str(map_id) not in wpa_data
        or team not in wpa_data[str(map_id)]
        or str(ct_score) not in wpa_data[str(map_id)][team]
        or str(t_score) not in wpa_data[str(map_id)][team][str(ct_score)]
    ):
        return {"error": "Invalid input"}

    # Get the win probability
    win_prob = wpa_data[str(map_id)][team][str(ct_score)][str(t_score)]

    return {
        "win_probability": win_prob,
    }


def _get_mapid(map_name: str) -> int:
    """Helper to get the map_id from map_name.

    Returns:
            int with the map_id

    """
    map_dict = {
        "de_cache": 29,
        "de_mirage": 32,
        "de_inferno": 33,
        "de_nuke": 34,
        "de_train": 35,
        "de_cbble": 39,
        "de_overpass": 40,
        "de_vertigo": 46,
        "de_ancient": 47,
        "de_anubis": 48,
    }

    if map_name in map_dict:
        return map_dict[map_name]
    raise ValueError
