SIMPLE_WP_MODEL = None
ADV_WP_MODEL = None


def state_win_probability(frame, model):
    """Predicts the win probability of a given frame.

    Args:
        frame (dict): Dict output of a frame generated from the DemoParser class

    Returns:
        A dictionary containing the CT and T round win probabilities
    """
    raise NotImplementedError


def round_win_probability(ct_score, t_score, map):
    """Estimates of game win probability using information from the HLTV win matrix for a given map and score.

    Args:
        ct_score (dict): CT Score
        t_score (dict): T Score
        map (dict): Map the demo is from

    Returns:
        A dictionary containing the CT game win, T game win and Draw probabilities
    """
    return NotImplementedError
