"""Methodology to calculate Kill, Assist, Survival, and Trade (KAST) %"""
import pandas as pd
from typing import Literal

from awpy.parser.models.demo import Demo


def kast(demo: Demo) -> pd.DataFrame:
    kill_df = demo.kills
    tick_df = demo.ticks

    kill_rounds, assist_rounds, trade_rounds, survival_rounds = get_kast_components(
        kill_df, tick_df
    )
    all_steamids = get_all_steamids(
        kill_rounds, assist_rounds, trade_rounds, survival_rounds
    )

    kast_data = calculate_kast(
        all_steamids, kill_rounds, assist_rounds, trade_rounds, survival_rounds, tick_df
    )
    return prepare_kast_df(kast_data)


def get_kast_components(
    kill_df: pd.DataFrame, tick_df: pd.DataFrame
) -> tuple[dict, dict, dict, dict]:
    kills = aggregate_kast_rounds(kill_df, "attacker_steamid")
    assists = aggregate_kast_rounds(kill_df, "assister_steamid")
    trades = aggregate_kast_rounds(kill_df[kill_df["was_traded"]], "victim_steamid")
    survivals = get_survival_rounds(tick_df)
    return kills, assists, trades, survivals


def aggregate_kast_rounds(df: pd.DataFrame, group_col: str) -> dict:
    return df.groupby(group_col)["round_num"].unique().to_dict()


def get_survival_rounds(tick_df: pd.DataFrame) -> dict:
    end_ticks = (
        tick_df[tick_df["side"].isin(["t", "ct"])]
        .groupby(["steamid", "round_num"])
        .tail(1)
    )
    survival_rounds = end_ticks[end_ticks["is_alive"] == True]
    return survival_rounds.groupby("steamid")["round_num"].unique().to_dict()


def get_all_steamids(*args: dict) -> set:
    all_steamids = set()
    for arg in args:
        all_steamids.update(arg.keys())
    return all_steamids


def calculate_kast(
    all_steamids: set,
    kills: dict,
    assists: dict,
    trades: dict,
    survivals: dict,
    tick_df: pd.DataFrame,
) -> dict:
    kast = {}
    for steamid in all_steamids:
        total_rounds = calculate_total_rounds_for_side(steamid, "total", tick_df)
        kast[steamid] = {
            "total": calculate_kast_for_side(
                steamid, kills, assists, trades, survivals, total_rounds
            )
        }
    return kast


def prepare_kast_df(kast_data: dict) -> pd.DataFrame:
    kast_df = (
        pd.DataFrame.from_dict(kast_data, orient="index")
        .reset_index()
        .rename(columns={"index": "steamid"})
    )
    kast_df["side"] = "total"
    kast_df = kast_df[["steamid", "side", "total"]]
    kast_df.columns = ["steamid", "side", "kast"]
    return kast_df


def calculate_total_rounds_for_side(
    steamid: int, side: Literal["ct", "t", "total"], tick_df: pd.DataFrame
) -> int:
    start_ticks = (
        tick_df[tick_df["side"].isin(["t", "ct"])]
        .groupby(["steamid", "round_num"])
        .head(1)
    )
    start_ticks_by_id = start_ticks[start_ticks["steamid"] == steamid]
    if side == "total":
        return start_ticks_by_id.shape[0]
    elif side == "ct":
        return start_ticks_by_id[start_ticks_by_id["side"] == "ct"].shape[0]
    elif side == "t":
        return start_ticks_by_id[start_ticks_by_id["side"] == "t"].shape[0]
    else:
        raise ValueError("Invalid side provided. Only t, ct, or total")


def calculate_kast_for_side(
    steamid: int,
    kills: dict,
    assists: dict,
    trades: dict,
    survivals: dict,
    total_rounds: int,
) -> float:
    kill_rounds = kills.get(steamid, [])
    assist_rounds = assists.get(steamid, [])
    trade_rounds = trades.get(steamid, [])
    survival_rounds = survivals.get(steamid, [])
    rounds = set()
    rounds.update(kill_rounds)
    rounds.update(assist_rounds)
    rounds.update(trade_rounds)
    rounds.update(survival_rounds)
    return len(rounds) / total_rounds
