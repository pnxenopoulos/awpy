"""Parsing methods for game rounds of a Counter-Strike demo file."""

import pandas as pd
import warnings

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
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,  # This is 0 because start/official end can occur on same tick
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.BUYTIME_ENDED.value: 3,
        GameEvent.ROUND_END.value: 4,
    }
    return event_order


def map_round_end_reasons(reason_series: pd.Series) -> pd.Series:
    """Map the round end reasons to their string representation.

    Args:
        reason_series (pd.Series): A series of round end reasons represented as integers.

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
        event_order (dict): A dictionary mapping enums.GameEvent to an integer representing order.

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
        pd.DataFrame: A DataFrame with the round event data prepended with a round start event.
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


def parse_rounds(parsed_round_events: list[tuple]) -> pd.DataFrame:
    """Parse the rounds of the demofile.

    Args:
        parsed_round_events (list[tuple]): Output of parser.parse_events(...)

    Returns:
        pd.DataFrame: Pandas DataFrame with the parsed rounds data.
    """
    if len(parsed_round_events) == 0:
        warnings.warn("No round events found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=[
                "round_start",
                "freeze_time_end",
                "buy_time_end",
                "round_end",
                "round_end_official",
                "round_end_reason",
            ]
        )

    # Get the round events in dataframe order
    round_events = []
    for _, round_event in enumerate(parsed_round_events):
        round_event[1]["event"] = round_event[0]
        if round_event[0] == GameEvent.ROUND_END.value:
            round_events.append(round_event[1].loc[:, ["tick", "event", "reason"]])
        else:
            round_events.append(round_event[1].loc[:, ["tick", "event"]])
    round_event_df = pd.concat(round_events)

    # Ascribe order to event types and sort by tick and order
    event_order = {
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,  # This is 0 because start/official end can occur on same tick
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.BUYTIME_ENDED.value: 3,
        GameEvent.ROUND_END.value: 4,
    }
    round_event_df["order"] = round_event_df["event"].map(event_order)
    round_event_df["reason"] = round_event_df["reason"].astype("Int64")
    round_event_df["reason"] = round_event_df["reason"].map(
        {
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
            pd.NA: pd.NA,
        }
    )
    round_event_df = round_event_df.sort_values(by=["tick", "order"])
    first_event = round_event_df.iloc[0]["event"]
    match first_event:
        case GameEvent.ROUND_START.value:
            pass
        case _:
            # If the first event is not a round start, add a round start event
            round_event_df = pd.concat(
                [
                    pd.DataFrame(
                        {
                            "tick": [0],
                            "event": [GameEvent.ROUND_START.value],
                            "order": [1],
                            "reason": [pd.NA],
                        }
                    ),
                    round_event_df,
                ]
            )
    return create_round_df(round_event_df)


def create_round_df(round_event_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a DataFrame with the round events by matching start and end events.

    Args:
        round_event_df (pd.DataFrame): DataFrame with the round events.

    Returns:
        pd.DataFrame: DataFrame with the round events by matching start and end events.
    """
    # Sort the round event dataframe by tick and order
    round_event_df.sort_values(by=["tick", "order"], inplace=True)

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

    final_df["round_num"] = range(1, len(final_df) + 1)
    final_df["round_end_official"] = final_df["round_end_official"].fillna(
        final_df["round_end"]
    )

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
    return df
