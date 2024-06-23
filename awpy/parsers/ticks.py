"""Module for tick parsing functions."""

import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611

from awpy.parsers.utils import parse_col_types


def remove_nonplay_ticks(parsed_df: pd.DataFrame) -> pd.DataFrame:
    """Filter out non-play records from a dataframe.

    Args:
        parsed_df (pd.DataFrame): A dataframe with the columns...

    Returns:
        pd.DataFrame: A dataframe with the non-play records removed.
    """
    # Check if the required columns are in the dataframe
    for col in [
        "is_freeze_period",
        "is_warmup_period",
        "is_terrorist_timeout",
        "is_ct_timeout",
        "is_technical_timeout",
        "is_waiting_for_resume",
        "is_match_started",
        "game_phase",
    ]:
        if col not in parsed_df.columns:
            error_msg = f"{col} not found in dataframe."
            raise ValueError(error_msg)

    # Remove records which do not occur in-play
    parsed_df = parsed_df[
        (~parsed_df["is_freeze_period"])
        & (~parsed_df["is_warmup_period"])
        & (~parsed_df["is_terrorist_timeout"])
        & (~parsed_df["is_ct_timeout"])
        & (~parsed_df["is_technical_timeout"])
        & (~parsed_df["is_waiting_for_resume"])
        & (parsed_df["is_match_started"])
        & (
            parsed_df["game_phase"].isin(
                [
                    2,  # startgame
                    3,  # preround
                ]
            )
        )
    ]

    # Drop the state columns
    return parsed_df.drop(
        columns=[
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ]
    )


def parse_ticks(
    parser: DemoParser,
    player_props: list[str],
    other_props: list[str],
) -> pd.DataFrame:
    """Parse the ticks of the demofile.

    Args:
        parser (DemoParser): The parser object.
        player_props (list[str]): Player properties to parse.
        other_props (list[str]): World properties to parse.

    Returns:
        pd.DataFrame: The ticks for the demofile.
    """
    ticks_df = parser.parse_ticks(wanted_props=player_props + other_props)
    return parse_col_types(remove_nonplay_ticks(ticks_df))
