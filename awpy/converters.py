"""Converters for index-based fields."""

import pandas as pd


def map_hitgroup(series: pd.Series) -> pd.Series:
    """Map hitgroups to their names.

    Args:
        series (pd.Series): Series of hitgroup integers.

    Returns:
        pd.Series: Series of hitgroup names.
    """
    hitgroup_mapping = {
        0: "generic",
        1: "head",
        2: "chest",
        3: "stomach",
        4: "left arm",
        5: "right arm",
        6: "left leg",
        7: "right leg",
        8: "neck",
        10: "gear",
    }
    return series.map(
        lambda x: hitgroup_mapping.get(x)  # pylint: disable=unnecessary-lambda
    )


def map_round_end_reasons(series: pd.Series) -> pd.Series:
    """Map round end reasons to their names.

    Args:
        series (pd.Series): Series of round end reason integers.

    Returns:
        pd.Series: Series of round end reason names.
    """
    round_end_reason_mapping = {
        0: "still_in_progress",
        1: "target_bombed",
        2: "vip_escaped",
        3: "vip_killed",
        4: "t_escaped",
        5: "ct_stopped_escape",
        6: "t_stopped",
        7: "bomb_defused",
        8: "ct_win",
        9: "t_win",
        10: "draw",
        11: "hostages_rescued",
        12: "target_saved",
        13: "hostages_not_rescued",
        14: "t_not_escaped",
        15: "vip_not_escaped",
        16: "game_start",
        17: "t_surrender",
        18: "ct_surrender",
        19: "t_planted",
        20: "cts_reached_hostage",
    }
    return series.map(
        lambda x: round_end_reason_mapping.get(x)  # pylint: disable=unnecessary-lambda
    )


def map_game_phase(series: pd.Series) -> pd.Series:
    """Map game phases to their names.

    Args:
        series (pd.Series): Series of game phase integers.

    Returns:
        pd.Series: Series of game phase names.
    """
    game_phase_mapping = {
        0: "init",
        1: "pregame",
        2: "startgame",
        3: "preround",
        4: "teamwin",
        5: "restart",
        6: "stalemate",
        7: "gameover",
    }
    return series.map(
        lambda x: game_phase_mapping.get(x)  # pylint: disable=unnecessary-lambda
    )
