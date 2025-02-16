"""Module for time and clock parsing functions."""

import math

import polars as pl

import awpy.constants
import awpy.parsers.utils


def parse_times(df_to_add_times: pl.DataFrame, rounds_df: pl.DataFrame, tick_col: str = "tick") -> pl.DataFrame:
    """Augment a tick DataFrame with timing information derived from round phase changes.

    This function processes the rounds DataFrame to extract key phase change times (specified by
    the columns "start", "freeze_end", "official_end", and "bomb_plant") by "melting" the DataFrame
    into a long format. It then performs an asof join with the tick DataFrame so that for each tick,
    the most recent phase change time (i.e. the maximum phase_time that is less than or equal to the tick)
    is identified. The function computes the difference between the tick value and the phase change time,
    yielding the number of ticks that have elapsed since the last phase change.

    The output DataFrame includes:
      - All original columns from df_to_add_times.
      - "ticks_since_phase_change": The number of ticks elapsed since the last phase change.
      - "last_phase_change": The name of the phase (one of "start", "freeze_end", "official_end", "bomb_plant")
        corresponding to the last phase change before each tick.

    Parameters:
        df_to_add_times (pl.DataFrame): A Polars DataFrame containing tick data. Must include a column
            designated by tick_col (default "tick") representing the tick count.
        rounds_df (pl.DataFrame): A Polars DataFrame containing round timing information with phase change columns.
        tick_col (str, optional): The name of the column in df_to_add_times holding tick values.
            Defaults to "tick".

    Returns:
        pl.DataFrame: The input tick DataFrame augmented with two new columns:
            - "ticks_since_phase_change": Ticks elapsed since the last phase change.
            - "last_phase_change": The phase (from the set {"start", "freeze_end", "official_end", "bomb_plant"})
              corresponding to the last phase change.

    Example:
        >>> augmented_df = parse_times(ticks_df, rounds_df, tick_col="tick")
    """
    # Define the phase columns.
    phase_cols = ["start", "freeze_end", "official_end", "bomb_plant"]

    # Melt the rounds_df so that all phase times are in one column.
    phase_df = (
        rounds_df.select(phase_cols)
        .melt(value_name="phase_time")  # now we have "variable" and "phase_time" columns
        .filter(pl.col("phase_time").is_not_null())  # drop any nulls if present
        .sort("phase_time")  # sort by time; required for join_asof
    ).with_columns(
        pl.col("phase_time").cast(pl.Int32)  # cast to int32 for join_asof
    )

    # Ensure the tick dataframe is sorted by tick.
    df_to_add_times = df_to_add_times.sort(tick_col)

    # Do an asof join: for each tick, find the last phase_time that is <= tick.
    joined = df_to_add_times.join_asof(phase_df, left_on=tick_col, right_on="phase_time", strategy="backward")

    # Compute the difference: ticks since the last phase change.
    joined = joined.with_columns((pl.col(tick_col) - pl.col("phase_time")).alias("ticks_since_phase_change"))

    # In case there is no phase change before a given tick, fill null with the tick value.
    joined = joined.with_columns(pl.col("ticks_since_phase_change").fill_null(pl.col(tick_col)))

    # Rename the "variable" column to "last_phase_change".
    return joined.rename({"variable": "last_phase_change"}).drop("phase_time")


def apply_clock_column(
    df: pl.DataFrame,
    ticks_since_phase_change_col: str = "ticks_since_phase_change",
    tick_rate: int = 128,
    freeze_time: float = awpy.constants.DEFAULT_FREEZE_TIME_IN_SECS,
    round_time: float = awpy.constants.DEFAULT_ROUND_TIME_IN_SECS,
    bomb_time: float = awpy.constants.DEFAULT_BOMB_TIME_IN_SECS,
) -> pl.DataFrame:
    """Add a 'clock' column to a DataFrame that contains round timing information.

    The DataFrame must have at least the following columns:
      - `last_phase_change`: A string indicating the most recent phase change. Expected values are:
          "start", "freeze_end", or "bomb_plant".
      - A column (by default named `ticks_since_phase_change`) which represents the number of ticks
        elapsed since the last phase change.

    The remaining time is calculated using the following logic:
      1. Map the value of `last_phase_change` to a phase duration (in seconds) as follows:
         - If last_phase_change is "start", use `freeze_time`.
         - If last_phase_change is "freeze_end", use `round_time`.
         - If last_phase_change is "bomb_plant", use `bomb_time`.
      2. Convert the selected phase duration to ticks by multiplying it with the provided `tick_rate`.
      3. Compute the remaining ticks as:

             remaining_ticks = (phase_duration_in_seconds * tick_rate) - ticks_since_phase_change

         Negative remaining ticks are clamped to 0.
      4. Convert the remaining ticks to seconds (rounding up) and then format the result as MM:SS.

    Parameters:
        df (pl.DataFrame): Input DataFrame containing round timing information.
        ticks_since_phase_change_col (str, optional): Column name for ticks since the last phase change.
            Defaults to "ticks_since_phase_change".
        tick_rate (int, optional): Server tick rate. Defaults to 128.
        freeze_time (float, optional): Duration of the freeze phase in seconds. Used when
            last_phase_change is "start". Defaults to awpy.constants.DEFAULT_FREEZE_TIME_IN_SECS.
        round_time (float, optional): Duration of the round phase in seconds. Used when
            last_phase_change is "freeze_end". Defaults to awpy.constants.DEFAULT_ROUND_TIME_IN_SECS.
        bomb_time (float, optional): Duration of the bomb phase in seconds. Used when
            last_phase_change is "bomb_plant". Defaults to awpy.constants.DEFAULT_BOMB_TIME_IN_SECS.

    Returns:
        pl.DataFrame: The original DataFrame with an added 'clock' column representing the remaining
                      time in the current phase as a string in MM:SS format.

    Raises:
        ValueError: If the DataFrame is missing the required columns ('last_phase_change' or the specified
                    ticks_since_phase_change_col).
        ValueError: If a row's 'last_phase_change' value is not one of the expected phase names.
        ValueError: If a row's ticks_since_phase_change value is negative.
    """
    # Verify required columns exist.
    awpy.parsers.utils.validate_required_columns(df, {"last_phase_change", ticks_since_phase_change_col})

    # Mapping from phase labels to the phase durations (in seconds) using the updated logic:
    # "start"       -> freeze_time,
    # "freeze_end"  -> round_time,
    # "bomb_plant"  -> bomb_time.
    phase_mapping = {
        "start": freeze_time,
        "freeze_end": round_time,
        "bomb_plant": bomb_time,
    }

    def _compute_clock_for_row(row: dict) -> str:
        phase = row["last_phase_change"]
        ticks_since = row[ticks_since_phase_change_col]

        if phase not in phase_mapping:
            invalid_phase_change_err_msg = (
                f"Invalid last_phase_change value: {phase}. Expected one of {list(phase_mapping.keys())}."
            )
            raise ValueError(invalid_phase_change_err_msg)
        if ticks_since < 0:
            raise ValueError("ticks_since_phase_change cannot be negative.")  # noqa: EM101

        # Compute the maximum ticks for the phase.
        max_time_ticks = phase_mapping[phase] * tick_rate

        # Calculate remaining ticks; if negative, clamp to 0 (time is up).
        remaining_ticks = max(0, max_time_ticks - ticks_since)

        # Convert ticks to seconds (rounding up).
        remaining_seconds = math.ceil(remaining_ticks / tick_rate)

        # Format the remaining time as MM:SS.
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        return f"{int(minutes):02}:{int(seconds):02}"

    # Apply the row-wise function to create the 'clock' column.
    # Note that we build a struct with the tick count column (using the provided name) and 'last_phase_change'.
    return df.with_columns(
        pl.struct([pl.col(ticks_since_phase_change_col), pl.col("last_phase_change")])
        .map_elements(_compute_clock_for_row, return_dtype=pl.String)
        .alias("clock")
    )
