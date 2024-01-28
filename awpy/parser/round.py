"""Parsing methods for game rounds of a Counter-Strike demo file."""

import warnings
import pandas as pd

from awpy.parser.enums import GameEvent


def parse_rounds(parsed_round_events: list[tuple]) -> pd.DataFrame:
    """Parse the rounds of the demofile.

    Args:
        parsed_round_events (list[tuple]): Output of parser.parse_events(...)

    Returns:
        pd.DataFrame: Pandas DataFrame with the parsed rounds data.
    """
    if not parsed_round_events:
        warnings.warn("No round events found in the demofile.", stacklevel=2)
        return empty_rounds_dataframe()

    round_events = process_round_events(parsed_round_events)
    round_event_df = pd.concat(round_events)

    return create_round_df(round_event_df)


def empty_rounds_dataframe() -> pd.DataFrame:
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
    round_events = [
        transform_round_event(event, event_order) for event in parsed_round_events
    ]
    return round_events


def get_round_event_order() -> dict:
    """Get the order of the round events.

    Returns:
        dict: A dictionary mapping enums.GameEvent to an integer representing order.
    """
    event_order = {
        # This is 0 because start/official end can occur on same tick
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.BUYTIME_ENDED.value: 3,
        GameEvent.ROUND_END.value: 4,
    }
    return event_order


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


def transform_round_event(round_event: tuple, event_order: dict) -> pd.DataFrame:
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


def prepend_round_start(round_event_df: pd.DataFrame) -> pd.DataFrame:
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
    round_event_df = round_event_df.sort_values(by=["tick", "order"])
    first_event = round_event_df.iloc[0]["event"]
    if first_event != GameEvent.ROUND_START.value:
        round_event_df = prepend_round_start(round_event_df)
    return round_event_df


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
    all_but_last = interval_index[:-1]
    last_interval = pd.Interval(
        left=round_df["round_start"].iloc[-1],
        right=round_df["round_end_official"].iloc[-1],
        closed="both",
    )
    fixed_interval_index = all_but_last.append(pd.IntervalIndex([last_interval]))
    intervals = pd.cut(df["tick"], fixed_interval_index)
    round_num_map = dict(zip(interval_index, round_df["round_num"], strict=True))
    df["round_num"] = intervals.map(round_num_map)
    df = df[~df["round_num"].isna()]
    return df
