"""Parsing methods for game rounds of a Counter-Strike demo file."""

import warnings

import pandas as pd

from awpy.parser.enums import GameEvent
from awpy.parser.models import Demo


def get_round_events(demo: Demo) -> pd.DataFrame:
    """_summary_

    Args:
        demo (Demo): _description_

    Returns:
        pd.DataFrame: _description_
    """
    # Get all the round events and concatenate them
    round_starts = demo.events.get("round_start")
    round_freeze_ends = demo.events.get("round_freeze_end")
    round_ends = demo.events.get("round_end")
    round_officially_ended = demo.events.get("round_officially_ended")

    round_events = pd.concat(
        [
            round_starts[["tick", "event_type"]],
            round_freeze_ends[["tick", "event_type"]],
            round_ends[["tick", "event_type"]],
            round_officially_ended[["tick", "event_type"]],
        ]
    )

    round_events["order"] = round_events["event_type"].map({
        # This is 0 because start/official end can occur on same tick
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.ROUND_END.value: 3,
    })
    round_events = round_events.sort_values(by=["tick", "order"]).reset_index(drop=True).drop(columns=["order"], axis=1)
    round_events = round_events[["tick", "event_type"]]

    # find first valid round
    start_idx = find_first_valid_round(round_events)
    round_events = round_events.iloc[start_idx:].reset_index(drop=True)

    round_events = filter_invalid_rounds(round_events)

    # find first round_start -> 

    return round_events

def find_first_valid_round(round_events: pd.DataFrame) -> int:
    """_summary_

    Args:
        round_events (pd.DataFrame): _description_

    Returns:
        int: _description_
    """
    start_idx = 0
    for i, row in round_events.iterrows():
        if i < 3: continue  # Need first valid START-FREEZE-END-OFFICIAL
        if row["event_type"] == "round_officially_ended":
            if round_events.iloc[i-1]["event_type"] == "round_end":
                if round_events.iloc[i-2]["event_type"] == "round_freeze_end":
                    if round_events.iloc[i-3]["event_type"] == "round_start":
                        start_idx = i-3
                        break
    return start_idx

def filter_invalid_rounds(round_events: pd.DataFrame) -> pd.DataFrame:
    """_summary_

    Args:
        round_events (pd.DataFrame): _description_

    Returns:
        pd.DataFrame: _description_
    """
    valid_rows = []
    for i, row in round_events.iterrows():
        if i < 3: continue
        if (i == round_events.shape[0]-1) and (row["event_type"] == "round_end"):
            valid_rows.extend([round_events.iloc[i-2:i-1], round_events.iloc[i-1:i], round_events.iloc[i:i+1]])
            break
        if row["event_type"] == "round_officially_ended":
            if round_events.iloc[i-1]["event_type"] == "round_end":
                if round_events.iloc[i-2]["event_type"] == "round_freeze_end":
                    if round_events.iloc[i-3]["event_type"] == "round_start":
                        valid_rows.extend([round_events.iloc[i-3:i-2], round_events.iloc[i-2:i-1], round_events.iloc[i-1:i], round_events.iloc[i:i+1]])
    return pd.concat(valid_rows, ignore_index=True)

def parse_rounds_df(parsed_round_events: list[tuple]) -> pd.DataFrame:
    """Parse the rounds of the demofile.

    Args:
        parsed_round_events (list[tuple]): Output of parser.parse_events(...)

    Returns:
        pd.DataFrame: Pandas DataFrame with the parsed rounds data.
    """
    if not parsed_round_events:
        warnings.warn("No round events found in the demofile.", stacklevel=2)
        return create_empty_rounds_dataframe()

    round_events = process_round_events(parsed_round_events)
    round_event_df = pd.concat(round_events)

    return create_round_df(round_event_df)


def create_empty_rounds_dataframe() -> pd.DataFrame:
    """Creates an empty dataframe for game rounds.

    Returns:
        pd.DataFrame: Empty Pandas DataFrame with the rounds column names..
    """
    columns = [
        "round_start",
        "freeze_time_end",
        "buy_time_end",
        "round_end",
        "round_end_official",
        "round_end_reason",
    ]
    return pd.DataFrame(columns=columns)


def process_round_events(parsed_round_events: list[tuple]) -> list:
    """Process and transform round events into DataFrames."""
    event_order = get_round_event_order()
    return [round_event_to_df(event, event_order) for event in parsed_round_events]


def get_round_event_order() -> dict:
    """Get the order of the round events.

    Returns:
        dict: A dictionary mapping enums.GameEvent to an integer representing order.
    """
    return {
        # This is 0 because start/official end can occur on same tick
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.BUYTIME_ENDED.value: 3,
        GameEvent.ROUND_END.value: 4,
    }


def map_round_end_reasons(reason_series: pd.Series) -> pd.Series:
    """Map the round end reasons to their string representation.

    Args:
        reason_series (pd.Series): A series of round end reasons represented
            as integers.

    Returns:
        pd.Series: A series of round end reasons represented as strings.
    """
    reasons_map = {
        0: "still_in_progress",
        1: "target_bombed",
        2: "vip_escaped",
        3: "vip_killed",
        4: "t_escape",
        5: "ct_stop_escape",
        6: "t_stopped",
        7: "bomb_defused",
        8: "ct_win",
        9: "t_win",
        10: "draw",
        11: "hostages_rescued",
        12: "target_saved",
        13: "hostages_not_rescued",
        14: "t_not_escaped",
        15: "vip_not_escaped",
        16: "game_start",
        17: "t_surrender",
        18: "ct_surrender",
        19: "t_planted",
        20: "cts_reached_hostage",
        pd.NA: pd.NA,  # pd.NA for handling missing values
    }
    return reason_series.astype("Int64").map(reasons_map)


def round_event_to_df(round_event: tuple, event_order: dict) -> pd.DataFrame:
    """Transform a round event into a DataFrame.

    Args:
        round_event (tuple): A tuple containing the event type and event data.
        event_order (dict): A dictionary mapping enums.GameEvent to an integer
            representing order.

    Returns:
        pd.DataFrame: A DataFrame with the round event data.
    """
    event_type, event_data = round_event
    event_data["event"] = event_type
    columns = (
        ["tick", "event", "reason"]
        if event_type == GameEvent.ROUND_END.value
        else ["tick", "event"]
    )
    event_df = event_data.loc[:, columns]
    event_df["order"] = event_df["event"].map(event_order)
    if "reason" in event_df.columns:
        event_df["reason"] = map_round_end_reasons(event_df["reason"])
    else:
        event_df["reason"] = pd.NA
    return event_df


def prepend_round_start_to_round_event(round_event_df: pd.DataFrame) -> pd.DataFrame:
    """Prepend a round start event to the round event DataFrame.

    Args:
        round_event_df (pd.DataFrame): A DataFrame with the round event data.

    Returns:
        pd.DataFrame: A DataFrame with the round event data prepended with a
            round start event.
    """
    start_event_df = pd.DataFrame(
        {
            "tick": [0],  # Assuming the start event should have a tick value of 0
            "event": [GameEvent.ROUND_START.value],
            "order": [1],  # The order value for a round start event
            "reason": [
                pd.NA
            ],  # NA for reason as it might not be applicable for a start event
        }
    )
    return pd.concat([start_event_df, round_event_df], ignore_index=True)


def create_round_df(round_event_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a DataFrame with the round events by matching start and end events.

    Args:
        round_event_df (pd.DataFrame): DataFrame with the round events.

    Returns:
        pd.DataFrame: DataFrame with the round events by matching start and end events.
    """
    # Prepend a round start event if it is not the first event
    round_event_df = (
        round_event_df.sort_values(by=["tick", "order"])
        .reset_index()
        .drop("index", axis=1)
    )
    # First, filter our erroneous round starts
    first_round_officially_ended_idx = round_event_df[
        round_event_df["event"] == "round_officially_ended"
    ].index.min()
    last_round_start_idx = round_event_df[
        (round_event_df["event"] == "round_start")
        & (round_event_df.index < first_round_officially_ended_idx)
    ].tick.idxmax()
    round_event_df = round_event_df.loc[last_round_start_idx:]
    first_event = round_event_df.iloc[0]["event"]
    if first_event != GameEvent.ROUND_START.value:
        round_event_df = prepend_round_start_to_round_event(round_event_df)

    # Initialize empty lists for each event type
    round_start = []
    freeze_time_end = []
    buy_time_end = []
    round_end = []
    round_end_official = []
    reason = []
    current_round = None

    # Iterate through the DataFrame and populate the lists
    for _, row in round_event_df.iterrows():
        if row["event"] == "round_start":
            if current_round is not None:
                # Append the collected events to the respective lists
                round_start.append(current_round.get("round_start", None))
                freeze_time_end.append(current_round.get("freeze_time_end", None))
                buy_time_end.append(current_round.get("buy_time_end", None))
                round_end.append(current_round.get("round_end", None))
                round_end_official.append(current_round.get("round_end_official", None))
                reason.append(current_round.get("reason", None))
            # Start a new round
            current_round = {"round_start": row["tick"]}
        elif current_round is not None:
            if row["event"] == "round_freeze_end":
                current_round["freeze_time_end"] = row["tick"]
            elif row["event"] == "buytime_ended":
                current_round["buy_time_end"] = row["tick"]
            elif row["event"] == "round_end":
                current_round["round_end"] = row["tick"]
                current_round["reason"] = row["reason"]
            elif row["event"] == "round_officially_ended":
                current_round["round_end_official"] = row["tick"]

    # Append the last collected round's events
    if current_round is not None:
        round_start.append(current_round.get("round_start", None))
        freeze_time_end.append(current_round.get("freeze_time_end", None))
        buy_time_end.append(current_round.get("buy_time_end", None))
        round_end.append(current_round.get("round_end", None))
        round_end_official.append(current_round.get("round_end_official", None))
        reason.append(current_round.get("reason", None))

    # Create a new DataFrame with the desired columns
    parsed_rounds_df = pd.DataFrame(
        {
            "round_start": round_start,
            "freeze_time_end": freeze_time_end,
            "buy_time_end": buy_time_end,
            "round_end": round_end,
            "round_end_official": round_end_official,
            "round_end_reason": reason,
        }
    )
    final_df = parsed_rounds_df[
        [
            "round_start",
            "freeze_time_end",
            "buy_time_end",
            "round_end",
            "round_end_official",
        ]
    ].astype("Int64")
    final_df["round_end_reason"] = parsed_rounds_df["round_end_reason"]
    final_df = final_df[~final_df["round_end_reason"].isna()]

    # Filter out rounds that have the same start and end, or that have erroneous data
    final_df["round_end_official"] = final_df["round_end_official"].fillna(
        final_df["round_end"]
    )
    final_df = final_df[
        final_df["round_start"] != final_df["round_end_official"]
    ].reset_index(drop=True)
    final_df = final_df[
        final_df["round_start"] <= final_df["freeze_time_end"]
    ].reset_index(drop=True)

    final_df["round_num"] = range(1, len(final_df) + 1)

    return final_df


def apply_round_num_to_df(df: pd.DataFrame, round_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns a round num to each row in the DataFrame.

    Args:
        df (pd.DataFrame): A dataframe with a `tick` column.
        round_df (pd.DataFrame): A dataframe with the round data from `parse_demo`.

    Returns:
        pd.DataFrame: A dataframe with the round num assigned to column `round_num`.
    """
    interval_index = pd.IntervalIndex.from_arrays(
        round_df["round_start"], round_df["round_end_official"], closed="left"
    )
    intervals = pd.cut(df["tick"], interval_index)
    round_num_map = dict(zip(interval_index, round_df["round_num"], strict=True))
    df["round_num"] = intervals.map(round_num_map)
    return df[~df["round_num"].isna()]
