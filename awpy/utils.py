"""Utilities for the Awpy package."""

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
