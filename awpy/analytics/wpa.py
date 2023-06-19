"""Will provide functionality for WPA and win probabilities.

WPA stands for Win Probability Added and is described in this paper:
https://arxiv.org/pdf/2011.01324.pdf.
"""
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
        map_name (str): Map the demo is from

    Returns:
        A dictionary containing the CT game win, T game win and Draw probabilities
    """
    raise NotImplementedError
