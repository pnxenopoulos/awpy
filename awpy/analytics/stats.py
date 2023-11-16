"""This module defines popular statistics used in CS:GO."""
import pandas as pd

from awpy.parser.models.demo import Demo


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
    damages_team_dmg_removed = damages[damages["side"] != damages["side_victim"]].copy()

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
        damages_team_dmg_removed.groupby(["attacker_steamid", "side"])
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
