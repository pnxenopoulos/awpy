"""Utility methods for stats module."""
import pandas as pd


def get_player_rounds(tick_df: pd.DataFrame) -> pd.DataFrame:
    clean_ticks = tick_df[
        tick_df["game_phase"].isin(["startgame", "preround", "teamwin", "restart"])
        & tick_df["side"].isin(["t", "ct"])
        & ~tick_df["round_num"].isna()
    ]
    return clean_ticks[["steamid", "side", "round_num"]].drop_duplicates()


def get_rounds_played(player_rounds: pd.DataFrame) -> pd.DataFrame:
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
