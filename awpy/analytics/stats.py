"""This module defines popular statistics used in CS:GO."""
import pandas as pd

from awpy.parser.models.demo import Demo

from typing import Literal


def adr(demo: Demo) -> pd.DataFrame:
    """Calculates average damage per round (ADR) for each player.

    Args:
        demo (Demo): The demo as produced from `awpy.parser.parse_demo`.

    Returns:
        pd.DataFrame: A dataframe with the columns: `steamid`, `side`, `dmg`,
        `rounds_played`, `adr`.
    """
    tick_df = demo["ticks"]

    # Get unique player-rounds and their counts
    clean_ticks = tick_df[
        tick_df["game_phase"].isin(["startgame", "preround", "teamwin", "restart"])
        & tick_df["side"].isin(["t", "ct"])
        & ~tick_df["round_num"].isna()
    ]
    player_rounds = clean_ticks[["steamid", "side", "round_num"]].drop_duplicates()
    player_rounds = player_rounds.groupby(["steamid", "side"]).size().reset_index()
    player_rounds.columns = ["steamid", "side", "rounds_played"]

    total_rounds = player_rounds.groupby("steamid")["rounds_played"].sum().reset_index()
    total_rounds["side"] = "total"
    total_rounds = total_rounds[["steamid", "side", "rounds_played"]]

    rounds_played = pd.concat([player_rounds, total_rounds], ignore_index=True)

    # Get viable ticks
    inplay_ticks = tick_df[["tick", "game_phase"]]
    inplay_ticks = inplay_ticks[
        inplay_ticks["game_phase"].isin(["startgame", "preround", "teamwin", "restart"])
    ]
    inplay_ticks = inplay_ticks.drop_duplicates()

    player_ticks = tick_df[["tick", "steamid", "side", "health"]]
    player_ticks = player_ticks[player_ticks["side"].isin(["t", "ct"])]
    player_ticks = player_ticks.drop("side", axis=1)
    player_ticks_shifted = player_ticks.copy()
    player_ticks_shifted["tick"] = player_ticks_shifted["tick"] + 1

    # Get damages only from viable ticks. Get player health from tick before.
    damage_df = demo["damages"]
    damages = damage_df.merge(inplay_ticks, on="tick", how="inner")

    damages = damages.merge(
        player_ticks,
        left_on=["attacker_steamid", "tick"],
        right_on=["steamid", "tick"],
        how="left",
        suffixes=("", "_attacker"),
    )
    damages = damages.merge(
        player_ticks_shifted,
        left_on=["victim_steamid", "tick"],
        right_on=["steamid", "tick"],
        how="left",
        suffixes=("", "_victim"),
    )

    # Remove team damage from ADR calculation.
    damages_team_dmg_removed = damages[
        damages["attacker_side"] != damages["victim_side"]
    ].copy()

    # Adjust damage to victim health if overkill.
    damages_team_dmg_removed["dmg_health_adj"] = damages_team_dmg_removed.apply(
        lambda x: min(x["dmg_health"], x["health_victim"]), axis=1
    )

    # Aggregate damages across sides
    total_dmg = (
        damages_team_dmg_removed.groupby("attacker_steamid")
        .dmg_health_adj.sum()
        .reset_index()
    )
    total_dmg["side"] = "total"
    total_dmg.columns = ["steamid", "dmg", "side"]

    side_dmg = (
        damages_team_dmg_removed.groupby(["attacker_steamid", "attacker_side"])
        .dmg_health_adj.sum()
        .reset_index()
    )
    side_dmg.columns = ["steamid", "side", "dmg"]

    # Calculate ADR by side
    agg_dmg = pd.concat([total_dmg, side_dmg], ignore_index=True)
    agg_dmg = agg_dmg.merge(
        rounds_played, left_on=["steamid", "side"], right_on=["steamid", "side"]
    )
    agg_dmg["adr"] = agg_dmg["dmg"] / agg_dmg["rounds_played"]

    return agg_dmg


def kast(demo: Demo) -> pd.DataFrame:
    """Calculates kill-assist-survive-trade % (KAST) for each player.

    Args:
        demo (Demo): The demo as produced from `awpy.parser.parse_demo`.

    Returns:
        pd.DataFrame: A dataframe with the columns: `steamid`, `side`, `rounds_played`,
            `kast`.
    """
    kill_df = demo["kills"]
    kill_df = kill_df[~kill_df["round_num"].isna()]
    tick_df = demo["ticks"]
    total_rounds = demo["rounds"].shape[0]

    kills = (
        kill_df.groupby("attacker_steamid")["round_num"]
        .unique()
        .rename("kill_rounds")
        .to_dict()
    )
    kills_side = (
        kill_df.groupby(["attacker_steamid", "attacker_side"])["round_num"]
        .unique()
        .rename("kill_rounds")
        .to_dict()
    )
    assists = (
        kill_df.groupby("assister_steamid")["round_num"]
        .unique()
        .rename("assist_rounds")
        .to_dict()
    )
    assists_side = (
        kill_df.groupby(["assister_steamid", "assister_side"])["round_num"]
        .unique()
        .rename("assist_rounds")
        .to_dict()
    )
    trades = (
        kill_df[kill_df["was_traded"] == True]
        .groupby("victim_steamid")["round_num"]
        .unique()
        .rename("trade_rounds")
        .to_dict()
    )
    trades_side = (
        kill_df[kill_df["was_traded"] == True]
        .groupby(["victim_steamid", "victim_side"])["round_num"]
        .unique()
        .rename("trade_rounds")
        .to_dict()
    )

    # Survivals
    end_ticks = (
        tick_df[tick_df["side"].isin(["t", "ct"])]
        .groupby(["steamid", "round_num"])
        .tail(1)
    )
    survival_rounds = end_ticks[["round_num", "steamid", "is_alive"]]
    survival_rounds = survival_rounds[survival_rounds["is_alive"] == True]
    survivals = (
        survival_rounds.groupby("steamid")["round_num"]
        .unique()
        .rename("survival_rounds")
        .to_dict()
    )

    all_steamids = set()
    all_steamids.update(kills.keys())
    all_steamids.update(assists.keys())
    all_steamids.update(trades.keys())
    all_steamids.update(survivals.keys())

    kast = {}

    for steamid in all_steamids:
        kast[steamid] = {"t": 0, "ct": 0, "total": 0}
        # Calculate total
        kill_rounds = kills.get(steamid, [])
        assist_rounds = assists.get(steamid, [])
        trade_rounds = trades.get(steamid, [])
        survival_rounds = survivals.get(steamid, [])
        rounds = set()
        rounds.update(kill_rounds)
        rounds.update(assist_rounds)
        rounds.update(trade_rounds)
        rounds.update(survival_rounds)
        total_rounds = _calculate_total_rounds_for_side(steamid, "total", tick_df)
        kast[steamid]["total"] = len(rounds) / total_rounds

    kast_df = (
        pd.DataFrame.from_dict(kast, orient="index", columns=["kast"])
        .reset_index()
        .rename(columns={"index": "steamid"})
    )
    kast_df["side"] = "total"

    return kast_df


def _calculate_total_rounds_for_side(
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


def _calculate_kast_for_side(
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
