"""Module for tick parsing functions."""

import polars as pl


def get_valid_ticks(tick_df: pl.DataFrame) -> pl.Series:
    """Get the valid ticks from a tick dataframe.

    This function filters out ticks that occur during certain invalid periods
    (warmup, various timeouts, waiting for resume) and retains ticks
    only when the match has started. It then returns a Series of unique tick values.

    Args:
        tick_df: A DataFrame containing tick data along with boolean columns
                 indicating various match periods.

    Returns:
        A pl.Series containing the unique tick values that meet the filtering criteria.
    """
    # Filter out ticks occurring in undesired periods.
    valid_ticks_df = tick_df.filter(
        pl.col("is_match_started")
        & (~pl.col("is_warmup_period"))
        & (~pl.col("is_terrorist_timeout"))
        & (~pl.col("is_ct_timeout"))
        & (~pl.col("is_technical_timeout"))
        & (~pl.col("is_waiting_for_resume"))
    )

    # Select the "tick" column and remove duplicate ticks.
    unique_ticks_df = valid_ticks_df.select("tick").unique(subset=["tick"])

    # Return the "tick" column as a pl.Series.
    return unique_ticks_df["tick"].sort()
