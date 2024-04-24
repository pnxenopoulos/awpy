"""Calculate impact and rating (like in HLTV)."""

import pandas as pd

from awpy import Demo
from awpy.stats import adr, kast
from awpy.stats.utils import get_player_rounds


def impact(demo: Demo) -> pd.DataFrame:
    """Calculates impact rating.

    Args:
        demo (Demo): A parsed Awpy demo.

    Returns:
        pd.DataFrame: A dataframe of the player info + impact.

    Raises:
        ValueError: If kills or ticks are missing in the parsed demo.
    """
    if demo.kills is None:
        missing_kills_error_msg = "Kills is missing in the parsed demo!"
        raise ValueError(missing_kills_error_msg)

    if demo.ticks is None:
        missing_ticks_error_msg = "Ticks is missing in the parsed demo!"
        raise ValueError(missing_ticks_error_msg)

    # Get total rounds by player
    player_total_rounds = get_player_rounds(demo)

    # Get kills and assists by side
    kills_total = (
        demo.kills.groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_ct = (
        demo.kills[demo.kills["attacker_side"] == "CT"]
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_t = (
        demo.kills[demo.kills["attacker_side"] == "TERRORIST"]
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )

    assists_total = (
        demo.kills.groupby(["assister_name", "assister_steamid"])
        .size()
        .reset_index(name="assists")
        .rename(columns={"assister_name": "name", "assister_steamid": "steamid"})
    )
    assists_ct = (
        demo.kills[demo.kills["assister_side"] == "CT"]
        .groupby(["assister_name", "assister_steamid"])
        .size()
        .reset_index(name="assists")
        .rename(columns={"assister_name": "name", "assister_steamid": "steamid"})
    )
    assists_t = (
        demo.kills[demo.kills["assister_side"] == "TERRORIST"]
        .groupby(["assister_name", "assister_steamid"])
        .size()
        .reset_index(name="assists")
        .rename(columns={"assister_name": "name", "assister_steamid": "steamid"})
    )

    stats_total = (
        player_total_rounds[player_total_rounds["side"] == "all"]
        .merge(kills_total, on=["name", "steamid"], how="left")
        .merge(assists_total, on=["name", "steamid"], how="left")
        .fillna(0)
    )
    stats_ct = (
        player_total_rounds[player_total_rounds["side"] == "CT"]
        .merge(kills_ct, on=["name", "steamid"], how="left")
        .merge(assists_ct, on=["name", "steamid"], how="left")
        .fillna(0)
    )
    stats_t = (
        player_total_rounds[player_total_rounds["side"] == "TERRORIST"]
        .merge(kills_t, on=["name", "steamid"], how="left")
        .merge(assists_t, on=["name", "steamid"], how="left")
        .fillna(0)
    )

    stats_total["side"] = "all"
    stats_ct["side"] = "CT"
    stats_t["side"] = "TERRORIST"

    impact_df = pd.concat([stats_total, stats_ct, stats_t])
    impact_df["impact"] = (
        2.13 * (impact_df["kills"] / impact_df["n_rounds"])
        + 0.42 * (impact_df["assists"] / impact_df["n_rounds"])
        - 0.41
    )

    return impact_df[["name", "steamid", "side", "impact"]]


def rating(demo: Demo) -> pd.DataFrame:
    """Calculates player rating, similar to HLTV.

    Args:
        demo (Demo): A parsed Awpy demo.

    Returns:
        pd.DataFrame: A dataframe of the player info + impact + rating.

    Raises:
        ValueError: If kills or ticks are missing in the parsed demo.
    """
    if demo.kills is None:
        missing_kills_error_msg = "Kills is missing in the parsed demo!"
        raise ValueError(missing_kills_error_msg)

    if demo.ticks is None:
        missing_ticks_error_msg = "Ticks is missing in the parsed demo!"
        raise ValueError(missing_ticks_error_msg)

    # Get total rounds by player
    player_total_rounds = get_player_rounds(demo)

    # Get deaths and assists
    kills_total = (
        demo.kills.groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_total["side"] = "all"
    kills_ct = (
        demo.kills[demo.kills["attacker_side"] == "CT"]
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_ct["side"] = "CT"
    kills_t = (
        demo.kills[demo.kills["attacker_side"] == "TERRORIST"]
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_t["side"] = "TERRORIST"
    kills = pd.concat([kills_total, kills_ct, kills_t])

    deaths_total = (
        demo.kills.groupby(["victim_name", "victim_steamid"])
        .size()
        .reset_index(name="deaths")
        .rename(columns={"victim_name": "name", "victim_steamid": "steamid"})
    )
    deaths_total["side"] = "all"
    deaths_ct = (
        demo.kills[demo.kills["victim_side"] == "CT"]
        .groupby(["victim_name", "victim_steamid"])
        .size()
        .reset_index(name="deaths")
        .rename(columns={"victim_name": "name", "victim_steamid": "steamid"})
    )
    deaths_ct["side"] = "CT"
    deaths_t = (
        demo.kills[demo.kills["victim_side"] == "TERRORIST"]
        .groupby(["victim_name", "victim_steamid"])
        .size()
        .reset_index(name="deaths")
        .rename(columns={"victim_name": "name", "victim_steamid": "steamid"})
    )
    deaths_t["side"] = "TERRORIST"
    deaths = pd.concat([deaths_total, deaths_ct, deaths_t])

    # KAST/ADR/Impact
    kast_df = kast(demo)
    adr_df = adr(demo)
    impact_df = impact(demo)

    # Merge and calculate
    rating_df = (
        player_total_rounds.merge(
            kast_df[["name", "steamid", "side", "kast"]],
            on=["name", "steamid", "side"],
            how="left",
        )
        .merge(
            adr_df[["name", "steamid", "side", "adr"]], on=["name", "steamid", "side"]
        )
        .merge(
            impact_df[["name", "steamid", "side", "impact"]],
            on=["name", "steamid", "side"],
        )
        .merge(kills, on=["name", "steamid", "side"])
        .merge(deaths, on=["name", "steamid", "side"])
    )
    rating_df["rating"] = (
        0.0073 * rating_df["kast"]
        + 0.3591 * (rating_df["kills"] / rating_df["n_rounds"])
        - 0.5329 * (rating_df["deaths"] / rating_df["n_rounds"])
        + 0.2372 * rating_df["impact"]
        + 0.0032 * rating_df["adr"]
        + 0.1587
    )

    return rating_df[["name", "steamid", "side", "n_rounds", "impact", "rating"]]
