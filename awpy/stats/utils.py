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
        ["name", "steamid", "team_name", "round"]
    ).head(1)[["name", "steamid", "team_name", "round"]]
    player_sides_by_round = player_sides_by_round.merge(demo.rounds, on="round")
    player_side_rounds = (
        player_sides_by_round.groupby(["name", "steamid", "team_name"])
        .size()
        .reset_index()
    )
    player_side_rounds.columns = ["name", "steamid", "team_name", "n_rounds"]
    player_total_rounds = (
        player_sides_by_round.groupby(["name", "steamid"]).size().reset_index()
    )
    player_total_rounds["team_name"] = "all"
    player_total_rounds.columns = ["name", "steamid", "n_rounds", "team_name"]
    player_total_rounds = player_total_rounds[
        ["name", "steamid", "team_name", "n_rounds"]
    ]

    return pd.concat([player_side_rounds, player_total_rounds])
