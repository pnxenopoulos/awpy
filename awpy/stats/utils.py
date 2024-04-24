"""Utilities for analytics methods."""

import pandas as pd

from awpy import Demo


def get_player_rounds(demo: Demo) -> pd.DataFrame:
    """Calculates number of rounds by player/side.

    Args:
        demo (Demo): A parsed Awpy demo.

    Returns:
        pd.DataFrame: A dataframe containing name, steamid, side, and n_rounds.

    Raises:
        ValueError: If ticks are missing in the parsed demo.
    """
    if demo.ticks is None:
        missing_ticks_error_msg = "Ticks is missing in the parsed demo!"
        raise ValueError(missing_ticks_error_msg)

    # Get rounds played by each player/side
    player_sides_by_round = demo.ticks.groupby(
        ["name", "steamid", "side", "round"]
    ).head(1)[["name", "steamid", "side", "round"]]
    player_side_rounds = (
        player_sides_by_round.groupby(["name", "steamid", "side"]).size().reset_index()
    )
    player_side_rounds.columns = ["name", "steamid", "side", "n_rounds"]
    player_total_rounds = (
        player_sides_by_round.groupby(["name", "steamid"]).size().reset_index()
    )
    player_total_rounds["side"] = "all"
    player_total_rounds.columns = ["name", "steamid", "n_rounds", "side"]
    player_total_rounds = player_total_rounds[["name", "steamid", "side", "n_rounds"]]

    return pd.concat([player_side_rounds, player_total_rounds])
