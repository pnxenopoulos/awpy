"""Calculates the Kill, Assist, Survival, Trade %."""

import pandas as pd


def calculate_trades(kills: pd.DataFrame, trade_ticks: int = 128 * 5) -> pd.DataFrame:
    """Calculates if kills are trades.

    A trade is a kill where the attacker of a player who recently died was
    killed shortly after the initial victim was killed.

    Args:
        kills (pd.DataFrame): A parsed Awpy kills dataframe.
        trade_ticks (int, optional): Length of trade time in ticks. Defaults to 128*5.

    Returns:
        pd.DataFrame: Adds `was_traded` columns to kills.
    """
    # Get all rounds
    rounds = kills["round"].unique()

    was_traded = []

    for r in rounds:
        kills_round = kills[kills["round"] == r]
        for _, row in kills_round.iterrows():
            kills_in_trade_window = kills_round[
                (kills_round["tick"] >= row["tick"] - trade_ticks)
                & (kills_round["tick"] <= row["tick"])
            ]
            if row["victim_name"] in kills_in_trade_window["attacker_name"].to_numpy():
                last_kill_by_attacker = None
                for __, attacker_row in kills_in_trade_window.iterrows():
                    if attacker_row["attacker_name"] == row["victim_name"]:
                        last_kill_by_attacker = attacker_row.name
                was_traded.append(last_kill_by_attacker)

    kills["was_traded"] = False
    kills.loc[was_traded, "was_traded"] = True

    return kills
