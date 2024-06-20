"""Utilities for the Awpy package."""

from typing import Literal

import pandas as pd


def apply_round_num(
    rounds_df: pd.DataFrame, df: pd.DataFrame, tick_col: str = "tick"
) -> pd.DataFrame:
    """Assigns appropriate round number based on tick.

    Args:
        rounds_df (pd.DataFrame): Parsed rounds from `Demo`.
        df (pd.DataFrame): Desired dataframe to apply round numbers.
        tick_col (str, optional): Name of tick column to check. Defaults to "tick".

    Raises:
        ValueError: If `tick` is not in `df` columns.

    Returns:
        pd.DataFrame: `df` with a `round` column to designate the round.
    """
    # We require the provided tick column column
    if tick_col not in df.columns:
        tick_col_does_not_exist_error_msg = "`tick` not found in dataframe."
        raise ValueError(tick_col_does_not_exist_error_msg)

    # Create intervals
    intervals = pd.IntervalIndex.from_arrays(
        rounds_df["start"], rounds_df["official_end"], closed="right"
    )

    # Add round
    df["round"] = intervals.get_indexer(df[tick_col]) + 1

    return df


def rename_columns_with_affix(
    df: pd.DataFrame,
    old_affix: str,
    new_affix: str,
    affix_type: Literal["prefix", "suffix"] = "prefix",
) -> pd.DataFrame:
    """Rename columns by replacing old_affix with new_affix.

    Args:
        df (pd.DataFrame): DataFrame whose columns are to be renamed.
        old_affix (str): Old affix to be replaced.
        new_affix (str): New affix to replace the old one.
        affix_type (str, optional): Prefix or suffix replacement. Defaults to 'prefix'.

    Returns:
        pd.DataFrame: DataFrame with renamed columns.
    """
    new_columns = {}
    for col in df.columns:
        if affix_type == "prefix" and col.startswith(old_affix):
            new_col = col.replace(
                old_affix, new_affix, 1
            )  # Replace only the first occurrence
            new_columns[col] = new_col
        elif affix_type == "suffix" and col.endswith(old_affix):
            new_col = col[::-1].replace(old_affix[::-1], new_affix[::-1], 1)[
                ::-1
            ]  # Reverse replace
            new_columns[col] = new_col
    return df.rename(columns=new_columns)
