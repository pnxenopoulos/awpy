"""Module for time and clock parsing functions."""

import math
from typing import Literal, Optional, Union

import pandas as pd
from pandas._libs.missing import NAType  # pylint: disable=no-name-in-module

ROUND_START_DEFAULT_TIME_IN_SECS = 20
FREEZE_DEFAULT_TIME_IN_SECS = 115
BOMB_DEFAULT_TIME_IN_SECS = 40

TimeVariants = Literal["start", "freeze", "bomb"]


def parse_clock(
    seconds_since_phase_change: int,
    max_time_ticks: Union[TimeVariants, int],
    tick_rate: int = 64,
    timings: Optional[dict] = None,
) -> str:
    """Parse the remaining time in a round or phase to a clock string.

    Args:
        seconds_since_phase_change (int): The number of seconds since the phase change.
        max_time_ticks (Union[Literal['start', 'freeze', 'bomb'], int]): The maximum
            time in ticks for the phase.
        tick_rate (int, optional): The tick rate of the server. Defaults to 64.
        timings (dict, optional): The timings for the round. Default dictionary is
            a dictionary of preset constants.

    Returns:
        str: The remaining time in MM:SS format.
    """
    if timings is None:
        timings = {
            "start": ROUND_START_DEFAULT_TIME_IN_SECS,
            "freeze": FREEZE_DEFAULT_TIME_IN_SECS,
            "bomb": BOMB_DEFAULT_TIME_IN_SECS,
        }

    if max_time_ticks == "start":
        max_time_ticks = timings["start"] * tick_rate
    elif max_time_ticks == "freeze":
        max_time_ticks = timings["freeze"] * tick_rate
    elif max_time_ticks == "bomb":
        max_time_ticks = timings["bomb"] * tick_rate

    # Calculate the remaining time in ticks
    remaining_ticks = max_time_ticks - seconds_since_phase_change

    # Convert remaining ticks to total seconds
    remaining_seconds = remaining_ticks / tick_rate

    # Round up the seconds
    remaining_seconds = math.ceil(remaining_seconds)

    # Calculate minutes and seconds
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    # Format as MM:SS with leading zeros
    return f"{int(minutes):02}:{int(seconds):02}"


def _find_clock_time(row: "pd.Series[int]") -> Union[str, NAType]:
    """Find the clock time for a row.

    Args:
        row: A row from a dataframe with ticks_since_* columns.

    Returns:
        str: The clock time in MM:SS format or NA if no valid time is found.
    """
    times: dict[TimeVariants, Union[int, NAType]] = {
        "start": row["ticks_since_round_start"],
        "freeze": row["ticks_since_freeze_time_end"],
        "bomb": row["ticks_since_bomb_plant"],
    }

    # Filter out NA values
    valid_times: dict[TimeVariants, int] = {
        k: v for k, v in times.items() if pd.notna(v)
    }

    if not valid_times:
        return pd.NA

    # Find the key with the minimum value among valid times
    # (Using valid_times.get causes three separate pyright warnings...)
    min_key: str = min(valid_times, key=lambda x: valid_times[x])
    return parse_clock(valid_times[min_key], min_key)


def parse_times(
    df: pd.DataFrame, rounds_df: pd.DataFrame, tick_col: str = "tick"
) -> pd.DataFrame:
    """Adds time_since_* columns to the dataframe.

    Args:
        df (pd.DataFrame): The dataframe to add the time columns to.
        rounds_df (pd.DataFrame): The rounds dataframe.
        tick_col (str): The column name of the tick column.

    Returns:
        pd.DataFrame: The dataframe with the timesince_* columns added.
    """
    if tick_col not in df.columns:
        tick_col_missing_msg = f"{tick_col} not found in dataframe."
        raise ValueError(tick_col_missing_msg)

    df_with_round_info = df.merge(rounds_df, on="round", how="left")
    df_with_round_info["ticks_since_round_start"] = (
        df_with_round_info[tick_col] - df_with_round_info["start"]
    )
    df_with_round_info["ticks_since_freeze_time_end"] = (
        df_with_round_info[tick_col] - df_with_round_info["freeze_end"]
    )
    df_with_round_info["ticks_since_bomb_plant"] = (
        df_with_round_info[tick_col] - df_with_round_info["bomb_plant"]
    )

    def remove_negative_values(x: Union[int, NAType]) -> Union[int, NAType]:
        """Handle negative values.

        Needed for type hints.
        """
        return pd.NA if pd.isna(x) or x < 0 else x

    # Apply the function to the selected columns
    for col in df_with_round_info.columns:
        if col.startswith("ticks_since_"):
            ticks_col: pd.Series[int] = df_with_round_info[col]
            df_with_round_info[col] = ticks_col.map(remove_negative_values).astype(
                pd.Int64Dtype()
            )

    df_with_round_info = df_with_round_info.drop(
        columns=[
            "start",
            "freeze_end",
            "end",
            "official_end",
            "winner",
            "reason",
            "bomb_plant",
        ]
    )

    df_with_round_info["clock"] = df_with_round_info.apply(_find_clock_time, axis=1)

    return df_with_round_info
