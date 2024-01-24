"""Methodology to calculate Average Damage per Round (ADR)"""
import pandas as pd

from awpy.parser.models.demo import Demo
from awpy.stats.utils import get_player_rounds, get_rounds_played


def get_damages(demo: Demo) -> pd.DataFrame:
    inplay_ticks = demo.ticks[
        demo.ticks["game_phase"].isin(["startgame", "preround", "teamwin", "restart"])
    ]
    inplay_ticks = inplay_ticks[["tick", "game_phase"]].drop_duplicates()
    player_ticks = demo.ticks[["tick", "steamid", "side", "health"]][
        demo.ticks["side"].isin(["t", "ct"])
    ].drop_duplicates()
    player_ticks_shifted = player_ticks.copy()
    player_ticks_shifted["tick"] += 1
    damages = demo.damages.merge(inplay_ticks, on="tick", how="inner")
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
    return damages[damages["attacker_side"] != damages["victim_side"]]


def calculate_aggregate_damage(damages: pd.DataFrame) -> pd.DataFrame:
    damages["dmg_health_adj"] = damages.apply(
        lambda x: min(x["dmg_health"], x["health_victim"]), axis=1
    )
    total_dmg = (
        damages.groupby("attacker_steamid")["dmg_health_adj"].sum().reset_index()
    )
    total_dmg["side"] = "total"
    side_dmg = (
        damages.groupby(["attacker_steamid", "attacker_side"])["dmg_health_adj"]
        .sum()
        .reset_index()
    )
    return pd.concat([total_dmg, side_dmg], ignore_index=True).rename(
        columns={"attacker_steamid": "steamid", "dmg_health_adj": "dmg"}
    )


def merge_with_rounds_played(
    agg_dmg: pd.DataFrame, rounds_played: pd.DataFrame
) -> pd.DataFrame:
    return agg_dmg.merge(rounds_played, on=["steamid", "side"])


def adr(demo: Demo) -> pd.DataFrame:
    player_rounds = get_player_rounds(demo.ticks)
    rounds_played = get_rounds_played(player_rounds)
    damages = get_damages(demo)
    agg_dmg = calculate_aggregate_damage(damages)
    agg_dmg = merge_with_rounds_played(agg_dmg, rounds_played)
    agg_dmg["adr"] = agg_dmg["dmg"] / agg_dmg["rounds_played"]
    return agg_dmg
