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
<<<<<<< HEAD
    if not demo.kills:
        missing_kills_error_msg = "Kills is missing in the parsed demo!"
        raise ValueError(missing_kills_error_msg)

    if not demo.ticks:
=======
    if demo.kills is None:
        missing_kills_error_msg = "Kills is missing in the parsed demo!"
        raise ValueError(missing_kills_error_msg)

    if demo.ticks is None:
>>>>>>> main
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
<<<<<<< HEAD
        demo.kills[demo.kills["attacker_side"] == "CT"]
=======
        demo.kills[demo.kills["attacker_team_name"] == "CT"]
>>>>>>> main
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_t = (
<<<<<<< HEAD
        demo.kills[demo.kills["attacker_side"] == "TERRORIST"]
=======
        demo.kills[demo.kills["attacker_team_name"] == "TERRORIST"]
>>>>>>> main
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
<<<<<<< HEAD
        demo.kills[demo.kills["assister_side"] == "CT"]
=======
        demo.kills[demo.kills["assister_team_name"] == "CT"]
>>>>>>> main
        .groupby(["assister_name", "assister_steamid"])
        .size()
        .reset_index(name="assists")
        .rename(columns={"assister_name": "name", "assister_steamid": "steamid"})
    )
    assists_t = (
<<<<<<< HEAD
        demo.kills[demo.kills["assister_side"] == "TERRORIST"]
=======
        demo.kills[demo.kills["assister_team_name"] == "TERRORIST"]
>>>>>>> main
        .groupby(["assister_name", "assister_steamid"])
        .size()
        .reset_index(name="assists")
        .rename(columns={"assister_name": "name", "assister_steamid": "steamid"})
    )

    stats_total = (
<<<<<<< HEAD
        player_total_rounds[player_total_rounds["side"] == "all"]
=======
        player_total_rounds[player_total_rounds["team_name"] == "all"]
>>>>>>> main
        .merge(kills_total, on=["name", "steamid"], how="left")
        .merge(assists_total, on=["name", "steamid"], how="left")
        .fillna(0)
    )
    stats_ct = (
<<<<<<< HEAD
        player_total_rounds[player_total_rounds["side"] == "CT"]
=======
        player_total_rounds[player_total_rounds["team_name"] == "CT"]
>>>>>>> main
        .merge(kills_ct, on=["name", "steamid"], how="left")
        .merge(assists_ct, on=["name", "steamid"], how="left")
        .fillna(0)
    )
    stats_t = (
<<<<<<< HEAD
        player_total_rounds[player_total_rounds["side"] == "TERRORIST"]
=======
        player_total_rounds[player_total_rounds["team_name"] == "TERRORIST"]
>>>>>>> main
        .merge(kills_t, on=["name", "steamid"], how="left")
        .merge(assists_t, on=["name", "steamid"], how="left")
        .fillna(0)
    )

<<<<<<< HEAD
    stats_total["side"] = "all"
    stats_ct["side"] = "CT"
    stats_t["side"] = "TERRORIST"
=======
    stats_total["team_name"] = "all"
    stats_ct["team_name"] = "CT"
    stats_t["team_name"] = "TERRORIST"
>>>>>>> main

    impact_df = pd.concat([stats_total, stats_ct, stats_t])
    impact_df["impact"] = (
        2.13 * (impact_df["kills"] / impact_df["n_rounds"])
        + 0.42 * (impact_df["assists"] / impact_df["n_rounds"])
        - 0.41
    )

<<<<<<< HEAD
    return impact_df[["name", "steamid", "side", "impact"]]
=======
    return impact_df[["name", "steamid", "team_name", "impact"]]
>>>>>>> main


def rating(demo: Demo) -> pd.DataFrame:
    """Calculates player rating, similar to HLTV.

    Args:
        demo (Demo): A parsed Awpy demo.

    Returns:
        pd.DataFrame: A dataframe of the player info + impact + rating.

    Raises:
        ValueError: If kills or ticks are missing in the parsed demo.
    """
<<<<<<< HEAD
    if not demo.kills:
        missing_kills_error_msg = "Kills is missing in the parsed demo!"
        raise ValueError(missing_kills_error_msg)

    if not demo.ticks:
=======
    if demo.kills is None:
        missing_kills_error_msg = "Kills is missing in the parsed demo!"
        raise ValueError(missing_kills_error_msg)

    if demo.ticks is None:
>>>>>>> main
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
<<<<<<< HEAD
    kills_total["side"] = "all"
    kills_ct = (
        demo.kills[demo.kills["attacker_side"] == "CT"]
=======
    kills_total["team_name"] = "all"
    kills_ct = (
        demo.kills[demo.kills["attacker_team_name"] == "CT"]
>>>>>>> main
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
<<<<<<< HEAD
    kills_ct["side"] = "CT"
    kills_t = (
        demo.kills[demo.kills["attacker_side"] == "TERRORIST"]
=======
    kills_ct["team_name"] = "CT"
    kills_t = (
        demo.kills[demo.kills["attacker_team_name"] == "TERRORIST"]
>>>>>>> main
        .groupby(["attacker_name", "attacker_steamid"])
        .size()
        .reset_index(name="kills")
        .rename(columns={"attacker_name": "name", "attacker_steamid": "steamid"})
    )
<<<<<<< HEAD
    kills_t["side"] = "TERRORIST"
=======
    kills_t["team_name"] = "TERRORIST"
>>>>>>> main
    kills = pd.concat([kills_total, kills_ct, kills_t])

    deaths_total = (
        demo.kills.groupby(["victim_name", "victim_steamid"])
        .size()
        .reset_index(name="deaths")
        .rename(columns={"victim_name": "name", "victim_steamid": "steamid"})
    )
<<<<<<< HEAD
    deaths_total["side"] = "all"
    deaths_ct = (
        demo.kills[demo.kills["victim_side"] == "CT"]
=======
    deaths_total["team_name"] = "all"
    deaths_ct = (
        demo.kills[demo.kills["victim_team_name"] == "CT"]
>>>>>>> main
        .groupby(["victim_name", "victim_steamid"])
        .size()
        .reset_index(name="deaths")
        .rename(columns={"victim_name": "name", "victim_steamid": "steamid"})
    )
<<<<<<< HEAD
    deaths_ct["side"] = "CT"
    deaths_t = (
        demo.kills[demo.kills["victim_side"] == "TERRORIST"]
=======
    deaths_ct["team_name"] = "CT"
    deaths_t = (
        demo.kills[demo.kills["victim_team_name"] == "TERRORIST"]
>>>>>>> main
        .groupby(["victim_name", "victim_steamid"])
        .size()
        .reset_index(name="deaths")
        .rename(columns={"victim_name": "name", "victim_steamid": "steamid"})
    )
<<<<<<< HEAD
    deaths_t["side"] = "TERRORIST"
=======
    deaths_t["team_name"] = "TERRORIST"
>>>>>>> main
    deaths = pd.concat([deaths_total, deaths_ct, deaths_t])

    # KAST/ADR/Impact
    kast_df = kast(demo)
    adr_df = adr(demo)
    impact_df = impact(demo)

    # Merge and calculate
    rating_df = (
        player_total_rounds.merge(
<<<<<<< HEAD
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
=======
            kast_df[["name", "steamid", "team_name", "kast"]],
            on=["name", "steamid", "team_name"],
            how="left",
        )
        .merge(
            adr_df[["name", "steamid", "team_name", "adr"]],
            on=["name", "steamid", "team_name"],
        )
        .merge(
            impact_df[["name", "steamid", "team_name", "impact"]],
            on=["name", "steamid", "team_name"],
        )
        .merge(kills, on=["name", "steamid", "team_name"])
        .merge(deaths, on=["name", "steamid", "team_name"])
>>>>>>> main
    )
    rating_df["rating"] = (
        0.0073 * rating_df["kast"]
        + 0.3591 * (rating_df["kills"] / rating_df["n_rounds"])
        - 0.5329 * (rating_df["deaths"] / rating_df["n_rounds"])
        + 0.2372 * rating_df["impact"]
        + 0.0032 * rating_df["adr"]
        + 0.1587
    )

<<<<<<< HEAD
    return rating_df[["name", "steamid", "side", "n_rounds", "impact", "rating"]]
=======
    return rating_df[["name", "steamid", "team_name", "n_rounds", "impact", "rating"]]
>>>>>>> main
