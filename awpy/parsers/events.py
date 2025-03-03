"""Module for event parsing functions."""

import polars as pl

import awpy.converters
import awpy.parsers.utils


def parse_kills(df: pl.DataFrame) -> pl.DataFrame:
    """Parse kill event data from the given DataFrame.

    This function standardizes kill event data by renaming columns with the prefix "user_" to "victim_".
    In addition, it processes the "hitgroup" column by mapping its values using the HITGROUP_MAP converter,
    thereby producing a DataFrame where hit groups are standardized for further analysis.

    Args:
        df (pl.DataFrame): A Polars DataFrame containing raw kill event data, with columns starting with "user_"
                           (e.g., "user_name", "user_health", etc.) and a "hitgroup" column.

    Returns:
        pl.DataFrame: A standardized DataFrame of kill events with "victim_" prefixed columns
            and a mapped "hitgroup" column.
    """
    return awpy.parsers.utils.rename_columns_with_affix(df, old_affix="user_", new_affix="victim_").with_columns(
        pl.col("hitgroup")
        .map_elements(lambda h: awpy.converters.HITGROUP_MAP.get(h, h), return_dtype=pl.String)
        .alias("hitgroup")
    )


def parse_damages(df: pl.DataFrame) -> pl.DataFrame:
    """Parse damage event data from the given DataFrame.

    This function standardizes damage event data by renaming columns with the prefix "user_" to "victim_".
    It replaces the values in the "hitgroup" column using the HITGROUP_MAP converter, and it computes a new column,
    "dmg_health_real", which represents the effective damage applied to the victim's health.
    The effective damage is calculated as the minimum of "dmg_health" and
        "victim_health" (i.e. damage cannot exceed the victim's remaining health).

    Args:
        df (pl.DataFrame): A Polars DataFrame containing raw damage event data, with columns starting with "user_"
                           and columns "dmg_health" and "hitgroup".

    Returns:
        pl.DataFrame: A standardized DataFrame of damage events with "victim_" prefixed columns, a
            replaced "hitgroup" column, and a computed "dmg_health_real" column.
    """
    return awpy.parsers.utils.rename_columns_with_affix(df, old_affix="user_", new_affix="victim_").with_columns(
        pl.col("hitgroup").map_elements(lambda h: awpy.converters.HITGROUP_MAP.get(h, h), return_dtype=pl.String),
        pl.when(pl.col("dmg_health") > pl.col("victim_health"))
        .then(pl.col("victim_health"))
        .otherwise(pl.col("dmg_health"))
        .alias("dmg_health_real"),
    )


def parse_footsteps(df: pl.DataFrame) -> pl.DataFrame:
    """Parse footstep event data from the given DataFrame.

    This function standardizes footstep event data by renaming columns with the prefix "user_" to "player_".
    This ensures that the resulting DataFrame uses a consistent naming convention for player-related data.

    Args:
        df (pl.DataFrame): A Polars DataFrame containing raw footstep event data with columns starting with "user_".

    Returns:
        pl.DataFrame: A standardized DataFrame of footstep events with columns renamed to start with "player_".
    """
    return awpy.parsers.utils.rename_columns_with_affix(df, old_affix="user_", new_affix="player_")


def parse_shots(df: pl.DataFrame) -> pl.DataFrame:
    """Parse shot event data from the given DataFrame.

    This function standardizes shot event data by renaming columns with the prefix "user_" to "player_".
    This results in a DataFrame that uses a consistent naming scheme for player-related information in shot events.

    Args:
        df (pl.DataFrame): A Polars DataFrame containing raw shot event data with columns starting with "user_".

    Returns:
        pl.DataFrame: A standardized DataFrame of shot events with columns renamed to start with "player_".
    """
    return awpy.parsers.utils.rename_columns_with_affix(df, old_affix="user_", new_affix="player_")
