"""Utility methods for stats module."""

import pandas as pd


def get_player_rounds(tick_df: pd.DataFrame) -> pd.DataFrame:
    """Get the rounds played by each player.

    Args:
        tick_df (pd.DataFrame): DataFrame containing player ticks.

    Returns:
        pd.DataFrame: DataFrame with the rounds played by each player.
    """
    clean_ticks = tick_df[
        tick_df["game_phase"].isin(["startgame", "preround", "teamwin", "restart"])
        & tick_df["side"].isin(["t", "ct"])
        & ~tick_df["round_num"].isna()
    ]
    return clean_ticks[["steamid", "side", "round_num"]].drop_duplicates()


def get_rounds_played(player_rounds: pd.DataFrame) -> pd.DataFrame:
    """Get the number of rounds played by each player.

    Args:
        player_rounds (pd.DataFrame): DataFrame containing the rounds played by
            each player. Found from `get_player_rounds(...)`.

    Returns:
        pd.DataFrame: DataFrame with the number of rounds played by each player.
    """
    player_round_counts = (
        player_rounds.groupby(["steamid", "side"])
        .size()
        .reset_index(name="rounds_played")
    )
    total_round_counts = (
        player_round_counts.groupby("steamid")["rounds_played"].sum().reset_index()
    )
    total_round_counts["side"] = "total"
    return pd.concat([player_round_counts, total_round_counts], ignore_index=True)
