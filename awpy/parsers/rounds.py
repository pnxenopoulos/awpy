"""Module for round parsing functions."""

from typing import Union

import numpy as np
import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611


def _find_bomb_plant_tick(row: pd.Series, bomb_ticks: pd.Series) -> Union[int, float]:
    """Find the bomb plant tick for a round.

    Args:
        row: A row from a dataframe
        bomb_ticks: A series of bomb ticks

    Returns:
        The bomb plant tick for the round, or NaN if no bomb plant was found.
    """
    # Filter the bomb ticks that fall within the round's start and end
    plant_ticks = bomb_ticks[(bomb_ticks >= row["start"]) & (bomb_ticks <= row["end"])]
    # Return the first bomb plant tick if it exists, otherwise NaN
    return plant_ticks.iloc[0] if not plant_ticks.empty else np.nan


def parse_rounds(parser: DemoParser, events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the rounds of the demofile.

    Args:
        parser: The parser object.
        events: A dictionary of parsed events.

    Returns:
        The rounds for the demofile.

    Raises:
        KeyError: If a round-related event is not found in the events.
    """
    round_start = parser.parse_event("round_start")
    if len(round_start) == 0:
        round_start_missing_msg = "round_start not found in events."
        raise KeyError(round_start_missing_msg)
    round_start["event"] = "start"

    round_end = parser.parse_event("round_end")
    if len(round_end) == 0:
        round_end_missing_msg = "round_end not found in events."
        raise KeyError(round_end_missing_msg)
    round_end = round_end[~round_end["winner"].isna()]  # Remove None round ends
    round_end["event"] = "end"

    round_end_official = parser.parse_event("round_officially_ended")
    if len(round_end_official) == 0:
        round_end_official_missing_msg = "round_officially_ended not found in events."
        raise KeyError(round_end_official_missing_msg)
    round_end_official["event"] = "official_end"

    round_freeze_end = parser.parse_event("round_freeze_end")
    if len(round_freeze_end) == 0:
        round_freeze_end_missing_msg = "round_freeze_end not found in events."
        raise KeyError(round_freeze_end_missing_msg)
    round_freeze_end["event"] = "freeze_end"

    rounds = pd.concat(
        [
            round_start[["event", "tick"]],
            round_freeze_end[["event", "tick"]],
            round_end[["event", "tick"]],
            round_end_official[["event", "tick"]],
        ]
    )

    # Remove everything that happen on tick 0, except starts
    rounds = rounds[~((rounds["tick"] == 0) & (rounds["event"] != "start"))]

    # Then, order
    event_order = ["official_end", "start", "freeze_end", "end"]
    rounds["event"] = pd.Categorical(
        rounds["event"], categories=event_order, ordered=True
    )
    rounds = (
        rounds.sort_values(by=["tick", "event"])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Initialize an empty list to store the indices of rows to keep
    indices_to_keep = []

    # Loop through the DataFrame and check for the correct order of events
    full_sequence_offset = len(event_order)
    for i in range(len(rounds)):
        # Extract the current sequence of events
        current_sequence = rounds["event"].iloc[i : i + full_sequence_offset].tolist()
        # Check if the current sequence matches the correct order
        if current_sequence == ["start", "freeze_end", "end", "official_end"]:
            # If it does, add the indices of these rows to the list
            indices_to_keep.extend(range(i, i + full_sequence_offset))
        # Case for end of match where we might not get a round official end
        # Case for start of match where we might not get a freeze end
        elif current_sequence == ["start", "freeze_end", "end"] or current_sequence[
            0 : full_sequence_offset - 1
        ] == [
            "start",
            "end",
            "official_end",
        ]:
            indices_to_keep.extend(range(i, i + full_sequence_offset - 1))

    # Filter the DataFrame to keep only the rows with the correct sequence
    rounds_filtered = rounds.loc[indices_to_keep].reset_index(drop=True)
    rounds_filtered["round"] = (rounds_filtered["event"] == "start").cumsum()
    rounds_reshaped = rounds_filtered.pivot_table(
        index="round", columns="event", values="tick", aggfunc="first", observed=False
    ).reset_index(drop=True)
    rounds_reshaped = rounds_reshaped[
        ["start", "freeze_end", "end", "official_end"]
    ].astype("Int32")
    rounds_reshaped.columns = ["start", "freeze_end", "end", "official_end"]
    rounds_reshaped = rounds_reshaped.merge(
        round_end[
            [
                "tick",
                "winner",
                "reason",
            ]
        ],
        left_on="end",
        right_on="tick",
        how="left",
    )
    rounds_reshaped["round"] = rounds_reshaped.index + 1
    rounds_reshaped["official_end"] = rounds_reshaped["official_end"].fillna(
        rounds_reshaped["end"]
    )

    # Subset round columns
    rounds_df = rounds_reshaped[
        ["round", "start", "freeze_end", "end", "official_end", "winner", "reason"]
    ]
    rounds_df["bomb_plant"] = pd.NA
    rounds_df["bomb_plant"] = rounds_df["bomb_plant"].astype(pd.Int64Dtype())

    # Find the bomb plant ticks
    bomb_planted = events.get("bomb_planted")
    if bomb_planted.shape[0] == 0:
        return rounds_df

    rounds_df["bomb_plant"] = rounds_df.apply(
        _find_bomb_plant_tick, bomb_ticks=bomb_planted["tick"], axis=1
    ).astype(pd.Int64Dtype())

    return rounds_df
