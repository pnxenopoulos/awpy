"""Calculate impact and rating (like in HLTV)."""

import polars as pl

import awpy.constants
import awpy.demo
from awpy.stats import adr, kast


def impact(
    demo: awpy.demo.Demo,
    kills_coef: float = 2.13,
    assists_coef: float = 0.42,
    intercept: float = -0.41,
) -> pl.DataFrame:
    """Calculates impact rating using Polars.

    Args:
        demo (awpy.demo.Demo): A parsed Awpy demo with kills and ticks as Polars DataFrames.
        kills_coef (float, optional): Coefficient for kills in the impact formula. Defaults to 2.13.
        assists_coef (float, optional): Coefficient for assists in the impact formula. Defaults to 0.42.
        intercept (float, optional): Intercept in the impact formula. Defaults to -0.41.

    Returns:
        pl.DataFrame: A DataFrame of player info with impact rating. The DataFrame contains:
            - name (str): The player's name.
            - steamid (str): The player's Steam ID.
            - side (str): The team ("all", "ct", or "t").
            - impact (float): The calculated impact rating.

    Raises:
        ValueError: If kills or ticks are missing in the parsed demo.
    """
    # --- KILLS ---

    # Total kills (all)
    kills_total = (
        demo.kills.group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.count("attacker_name").alias("kills"))
        .with_columns(pl.lit("all").alias("side"))
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    # Kills for CT side
    kills_ct = (
        demo.kills.filter(pl.col("attacker_side") == awpy.constants.CT_SIDE)
        .group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.count("attacker_name").alias("kills"))
        .with_columns(pl.lit(awpy.constants.CT_SIDE).alias("side"))
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    # Kills for TERRORIST side
    kills_t = (
        demo.kills.filter(pl.col("attacker_side") == awpy.constants.T_SIDE)
        .group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.count("attacker_name").alias("kills"))
        .with_columns(pl.lit(awpy.constants.T_SIDE).alias("side"))
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )

    # --- ASSISTS ---

    # Total assists (all)
    assists_total = (
        demo.kills.group_by(["assister_name", "assister_steamid"])
        .agg(pl.count("assister_name").alias("assists"))
        .with_columns(pl.lit("all").alias("side"))
        .rename({"assister_name": "name", "assister_steamid": "steamid"})
    )
    # Assists for CT side
    assists_ct = (
        demo.kills.filter(pl.col("assister_side") == awpy.constants.CT_SIDE)
        .group_by(["assister_name", "assister_steamid"])
        .agg(pl.count("assister_name").alias("assists"))
        .with_columns(pl.lit(awpy.constants.CT_SIDE).alias("side"))
        .rename({"assister_name": "name", "assister_steamid": "steamid"})
    )
    # Assists for TERRORIST side
    assists_t = (
        demo.kills.filter(pl.col("assister_side") == awpy.constants.T_SIDE)
        .group_by(["assister_name", "assister_steamid"])
        .agg(pl.count("assister_name").alias("assists"))
        .with_columns(pl.lit(awpy.constants.T_SIDE).alias("side"))
        .rename({"assister_name": "name", "assister_steamid": "steamid"})
    )

    # --- Merge Kills & Assists with Rounds ---

    stats_total = (
        demo.player_round_totals.filter(pl.col("side") == "all")
        .join(kills_total, on=["name", "steamid"], how="left", suffix="_kills")
        .join(assists_total, on=["name", "steamid"], how="left", suffix="_assists")
        .fill_null(0)
    )
    stats_ct = (
        demo.player_round_totals.filter(pl.col("side") == "ct")
        .join(kills_ct, on=["name", "steamid"], how="left", suffix="_kills")
        .join(assists_ct, on=["name", "steamid"], how="left", suffix="_assists")
        .fill_null(0)
    )
    stats_t = (
        demo.player_round_totals.filter(pl.col("side") == "t")
        .join(kills_t, on=["name", "steamid"], how="left", suffix="_kills")
        .join(assists_t, on=["name", "steamid"], how="left", suffix="_assists")
        .fill_null(0)
    )

    # Combine the stats for all teams
    impact_df = pl.concat([stats_total, stats_ct, stats_t])
    # Calculate impact = 2.13*(kills/n_rounds) + 0.42*(assists/n_rounds) - 0.41
    impact_df = impact_df.with_columns(
        (
            kills_coef * (pl.col("kills") / pl.col("n_rounds"))
            + assists_coef * (pl.col("assists") / pl.col("n_rounds"))
            + intercept
        ).alias("impact")
    )

    return impact_df.select(["name", "steamid", "side", "impact"])


def rating(
    demo: awpy.demo.Demo,
    kast_coef: float = 0.0073,
    kills_coef: float = 0.3591,
    deaths_coef: float = -0.5329,
    impact_coef: float = 0.2372,
    adr_coef: float = 0.0032,
    intercept: float = 0.1587,
) -> pl.DataFrame:
    """Calculates player rating (similar to HLTV) using Polars.

    Args:
        demo (awpy.demo.Demo): A parsed Awpy demo with kills and ticks as Polars DataFrames.
        kast_coef (float, optional): Coefficient for KAST in the rating formula. Defaults to 0.0073.
        kills_coef (float, optional): Coefficient for kills in the rating formula. Defaults to 0.3591.
        deaths_coef (float, optional): Coefficient for deaths in the rating formula. Defaults to -0.5329.
        impact_coef (float, optional): Coefficient for impact in the rating formula. Defaults to 0.2372.
        adr_coef (float, optional): Coefficient for ADR in the rating formula. Defaults to 0.0032.
        intercept (float, optional): Intercept in the rating formula. Defaults to 0.1587.

    Returns:
        pl.DataFrame: A DataFrame of player info with additional columns:
            - n_rounds (int): Total rounds played.
            - impact (float): Impact rating.
            - rating (float): The overall calculated rating.

    Raises:
        ValueError: If kills or ticks are missing in the parsed demo.
    """
    # --- KILLS ---

    kills_total = (
        demo.kills.group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.count("attacker_name").alias("kills"))
        .with_columns(pl.lit("all").alias("side"))
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_ct = (
        demo.kills.filter(pl.col("attacker_side") == awpy.constants.CT_SIDE)
        .group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.count("attacker_name").alias("kills"))
        .with_columns(pl.lit(awpy.constants.CT_SIDE).alias("side"))
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_t = (
        demo.kills.filter(pl.col("attacker_side") == awpy.constants.T_SIDE)
        .group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.count("attacker_name").alias("kills"))
        .with_columns(pl.lit(awpy.constants.T_SIDE).alias("side"))
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills = pl.concat([kills_total, kills_ct, kills_t])

    # --- DEATHS ---

    deaths_total = (
        demo.kills.group_by(["victim_name", "victim_steamid"])
        .agg(pl.count("victim_name").alias("deaths"))
        .with_columns(pl.lit("all").alias("side"))
        .rename({"victim_name": "name", "victim_steamid": "steamid"})
    )
    deaths_ct = (
        demo.kills.filter(pl.col("victim_side") == awpy.constants.CT_SIDE)
        .group_by(["victim_name", "victim_steamid"])
        .agg(pl.count("victim_name").alias("deaths"))
        .with_columns(pl.lit(awpy.constants.CT_SIDE).alias("side"))
        .rename({"victim_name": "name", "victim_steamid": "steamid"})
    )
    deaths_t = (
        demo.kills.filter(pl.col("victim_side") == awpy.constants.T_SIDE)
        .group_by(["victim_name", "victim_steamid"])
        .agg(pl.count("victim_name").alias("deaths"))
        .with_columns(pl.lit(awpy.constants.T_SIDE).alias("side"))
        .rename({"victim_name": "name", "victim_steamid": "steamid"})
    )
    deaths = pl.concat([deaths_total, deaths_ct, deaths_t])

    # Get additional stats from other helper functions.
    # (Assuming these functions have been refactored to return Polars DataFrames.)
    kast_df = kast(demo)
    adr_df = adr(demo)
    impact_df = impact(demo)

    # --- Merge all stats ---
    rating_df = (
        demo.player_round_totals.join(
            kast_df.select(["name", "steamid", "side", "kast"]),
            on=["name", "steamid", "side"],
            how="left",
        )
        .join(
            adr_df.select(["name", "steamid", "side", "adr"]),
            on=["name", "steamid", "side"],
        )
        .join(
            impact_df.select(["name", "steamid", "side", "impact"]),
            on=["name", "steamid", "side"],
        )
        .join(kills, on=["name", "steamid", "side"])
        .join(deaths, on=["name", "steamid", "side"])
    )

    # Calculate rating using the weighted formula:
    rating_df = rating_df.with_columns(
        (
            kast_coef * pl.col("kast")
            + kills_coef * (pl.col("kills") / pl.col("n_rounds"))
            + deaths_coef * (pl.col("deaths") / pl.col("n_rounds"))
            + impact_coef * pl.col("impact")
            + adr_coef * pl.col("adr")
            + intercept
        ).alias("rating")
    )

    return rating_df.select(["name", "steamid", "side", "n_rounds", "impact", "rating"])
