"""Module for time and clock parsing functions."""

import math
from typing import Literal, Union

import pandas as pd

ROUND_START_DEFAULT_TIME_IN_SECS = 20
FREEZE_DEFAULT_TIME_IN_SECS = 115
BOMB_DEFAULT_TIME_IN_SECS = 40


def parse_clock(
    seconds_since_phase_change: int,
    max_time_ticks: Union[Literal["start", "freeze", "bomb"], int],
    tick_rate: int = 64,
) -> str:
    """Parse the remaining time in a round or phase to a clock string.

    Args:
        seconds_since_phase_change (int): The number of seconds since the phase change.
        max_time_ticks (Union[Literal['start', 'freeze', 'bomb'], int]): The maximum
            time in ticks for the phase.
        tick_rate (int, optional): The tick rate of the server. Defaults to 64.

    Returns:
        str: The remaining time in MM:SS format.
    """
    if max_time_ticks == "start":
        max_time_ticks = ROUND_START_DEFAULT_TIME_IN_SECS * tick_rate
    elif max_time_ticks == "freeze":
        max_time_ticks = FREEZE_DEFAULT_TIME_IN_SECS * tick_rate
    elif max_time_ticks == "bomb":
        max_time_ticks = BOMB_DEFAULT_TIME_IN_SECS * tick_rate

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


def _find_clock_time(row: pd.Series) -> str:
    """Find the clock time for a row.

    Args:
        row: A row from a dataframe with ticks_since_* columns.
    """
    times = {
        "start": row["ticks_since_round_start"],
        "freeze": row["ticks_since_freeze_time_end"],
        "bomb": row["ticks_since_bomb_plant"],
    }
    # Filter out NA values and find the key with the minimum value
    min_key = min((k for k in times if pd.notna(times[k])), key=lambda k: times[k])
    return parse_clock(times[min_key], min_key)


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

    # Apply the function to the selected columns
    for col in df_with_round_info.columns:
        if col.startswith("ticks_since_"):
            df_with_round_info[col] = (
                df_with_round_info[col]
                .map(lambda x: pd.NA if x < 0 else x)
                .astype(pd.Int64Dtype())
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
