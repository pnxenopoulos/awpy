"""Calculates Average Damage Per Round."""

import polars as pl

import awpy.constants
import awpy.demo


def adr(
    demo: awpy.demo.Demo,
    *,
    team_dmg: bool = False,
    self_dmg: bool = True,
) -> pl.DataFrame:
    """Calculates Average Damage Per Round (ADR) for each player.

    Args:
        demo (awpy.demo.Demo): A parsed demo object which has a Polars DataFrame in `demo.damages`.
        team_dmg (bool, optional): If True, remove team damage events (i.e. when the attacker and victim
                                   are on the same side). Defaults to False.
        self_dmg (bool, optional): If True, remove self damage events (i.e. when `attacker_name` is missing).
                                   Defaults to True.

    Returns:
        pl.DataFrame: A DataFrame containing columns: name, steamid, team_name, n_rounds, dmg, adr.

    Raises:
        ValueError: If damages are missing in the parsed demo.
    """
    # Get the damages DataFrame from the demo
    damages = demo.damages.clone()

    # Remove team damage events if specified
    if team_dmg:
        damages = damages.filter(pl.col("attacker_side") != pl.col("victim_side"))

    # Remove self damage events if specified
    if self_dmg:
        damages = damages.filter(pl.col("attacker_name").is_not_null())

    # Aggregate total damage for all rounds per player
    damages_all = (
        damages.group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.col("dmg_health_real").sum().alias("dmg"))
        .with_columns(pl.lit("all").alias("side"))
    )

    # Aggregate damage for ct side only
    damages_ct = (
        damages.filter(pl.col("attacker_side") == awpy.constants.CT_SIDE)
        .group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.col("dmg_health_real").sum().alias("dmg"))
        .with_columns(pl.lit("ct").alias("side"))
    )

    # Aggregate damage for t side only
    damages_t = (
        damages.filter(pl.col("attacker_side") == awpy.constants.T_SIDE)
        .group_by(["attacker_name", "attacker_steamid"])
        .agg(pl.col("dmg_health_real").sum().alias("dmg"))
        .with_columns(pl.lit("t").alias("side"))
    )

    # Combine the aggregated damage DataFrames
    damage_agg = pl.concat([damages_all, damages_ct, damages_t])

    # Rename columns for clarity
    damage_agg = damage_agg.rename({"attacker_name": "name", "attacker_steamid": "steamid"})

    # Merge the aggregated damage data with the rounds data
    adr_df = damage_agg.join(demo.player_round_totals, on=["name", "steamid", "side"], how="inner")

    # Calculate ADR = total damage / number of rounds played
    adr_df = adr_df.with_columns((pl.col("dmg") / pl.col("n_rounds")).alias("adr"))

    # Select and return the desired columns
    return adr_df.select(["name", "steamid", "side", "n_rounds", "dmg", "adr"])
