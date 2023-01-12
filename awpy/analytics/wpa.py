from awpy.types import GameFrame

SIMPLE_WP_MODEL = None
ADV_WP_MODEL = None


def state_win_probability(frame: GameFrame, model) -> dict:
    """Predicts the win probability of a given frame.

    Args:
        frame (dict): Dict output of a frame generated from the DemoParser class

    Returns:
        A dictionary containing the CT and T round win probabilities
    """
    raise NotImplementedError


def round_win_probability(ct_score: int, t_score: int, map_name: str) -> dict:
    """Estimates of game win probability using information from the HLTV win matrix for a given map and score.

    Args:
        ct_score (int): CT Score
        t_score (int): T Score
        map (str): Map the demo is from

    Returns:
        A dictionary containing the CT game win, T game win and Draw probabilities
    """
    raise NotImplementedError
