"""Parsing methods for game rounds of a Counter-Strike demo file."""

import pandas as pd

from awpy.parser.enums import GameEvent
from awpy.parser.models.demo import Demo


def parse_rounds(demo: Demo) -> pd.DataFrame:
    """Parses the rounds from the parsed demo file.

    Args:
        demo (Demo): The parsed demo file, computed from `parse_demo`.

    Returns:
        pd.DataFrame: A DataFrame with the round data (start/freezetime/end)
    """
    round_events = get_round_events(demo)

    # Get round ids (round number)
    round_events["round_id"] = (round_events["event_type"] == "round_start").cumsum()
    rounds = round_events.pivot_table(
        index="round_id", columns="event_type", values="tick", aggfunc="first"
    ).reset_index()
    rounds = rounds.reindex(
        columns=[
            "round_id",
            "round_start",
            "round_freeze_end",
            "round_end",
            "round_officially_ended",
        ]
    )
    rounds = rounds.reset_index(drop=True)

    # Add round end reasons
    round_ends: pd.DataFrame = demo.events.get("round_end")
    round_ends["round_end_reason"] = map_round_end_reasons(round_ends.reason)
    rounds = rounds.merge(
        round_ends[["tick", "round_end_reason"]],
        left_on="round_end",
        right_on="tick",
        how="left",
    )
    rounds = rounds.drop(columns="tick")

    # Fix any NA, change datatypes
    rounds["round_officially_ended"] = rounds["round_officially_ended"].fillna(
        rounds["round_end"]
    )
    for column in [
        "round_id",
        "round_start",
        "round_freeze_end",
        "round_end",
        "round_officially_ended",
        "bomb_plant",
    ]:
        rounds[column] = rounds[column].astype(int)

    # Get bomb plant information
    bomb_plants: pd.DataFrame = demo.events.get("bomb_planted")
    bomb_plants = apply_round_id_to_df(bomb_plants, rounds)
    rounds = rounds.merge(bomb_plants[["tick", "round_id"]], how="left", on="round_id")
    rounds = rounds.rename(columns={"tick": "bomb_plant"}).fillna(pd.NA)
    rounds["bomb_plant"] = pd.to_numeric(rounds["bomb_plant"], errors="coerce").astype(
        "Int64"
    )

    return rounds


def get_round_events(demo: Demo) -> pd.DataFrame:
    """Gets all round events and their ticks.

    Args:
        demo (Demo): The parsed demo file, computed from `parse_demo`.

    Returns:
        pd.DataFrame: A DataFrame with the round event and the tick it occurred at.
    """
    # Get all the round events and concatenate them
    round_starts: pd.DataFrame = demo.events.get("round_start")
    round_freeze_ends: pd.DataFrame = demo.events.get("round_freeze_end")
    round_ends: pd.DataFrame = demo.events.get("round_end")
    round_officially_ended: pd.DataFrame = demo.events.get("round_officially_ended")

    round_events = pd.concat(
        [
            round_starts[["tick", "event_type"]],
            round_freeze_ends[["tick", "event_type"]],
            round_ends[["tick", "event_type"]],
            round_officially_ended[["tick", "event_type"]],
        ]
    )

    round_events["order"] = round_events["event_type"].map(
        {
            # This is 0 because start/official end can occur on same tick
            GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
            GameEvent.ROUND_START.value: 1,
            GameEvent.ROUND_FREEZE_END.value: 2,
            GameEvent.ROUND_END.value: 4,
        }
    )
    round_events = (
        round_events.sort_values(by=["tick", "order"])
        .reset_index(drop=True)
        .drop(columns=["order"], axis=1)
    )
    round_events = round_events[["tick", "event_type"]]

    # find first valid round
    start_idx = find_first_valid_round(round_events)
    round_events = round_events.iloc[start_idx:].reset_index(drop=True)

    return filter_invalid_rounds(round_events)


def find_first_valid_round(round_events: pd.DataFrame) -> int:
    """Finds the first valid round in the round events.

    Args:
        round_events (pd.DataFrame): A DataFrame with the round events and the
            tick it occurred at. Computed from `get_round_events`.

    Returns:
        int: The index of the first valid round in the round events.
    """
    start_idx = 0
    for i, row in round_events.iterrows():
        if i < 3:
            continue  # Need first valid START-FREEZE-END-OFFICIAL
        if (
            (row["event_type"] == "round_officially_ended")
            and (round_events.iloc[i - 1]["event_type"] == "round_end")
            and (round_events.iloc[i - 2]["event_type"] == "round_freeze_end")
            and (round_events.iloc[i - 3]["event_type"] == "round_start")
        ):
            start_idx = i - 3
            break
    return start_idx


def filter_invalid_rounds(round_events: pd.DataFrame) -> pd.DataFrame:
    """Filters out invalid rounds from the round events.

    Rounds follow the pattern: START-FREEZE-END-OFFICIAL

    Args:
        round_events (pd.DataFrame): A DataFrame with the round events and the
            tick it occurred at. Computed from `get_round_events`.

    Returns:
        pd.DataFrame: A DataFrame with the valid round events.
    """
    valid_rows = []
    for i, row in round_events.iterrows():
        if i < 3:
            continue
        if (i == round_events.shape[0] - 1) and (row["event_type"] == "round_end"):
            valid_rows.extend(
                [
                    round_events.iloc[i - 2 : i - 1],
                    round_events.iloc[i - 1 : i],
                    round_events.iloc[i : i + 1],
                ]
            )
            break
        if (
            (row["event_type"] == "round_officially_ended")
            and (round_events.iloc[i - 1]["event_type"] == "round_end")
            and (round_events.iloc[i - 2]["event_type"] == "round_freeze_end")
            and (round_events.iloc[i - 3]["event_type"] == "round_start")
        ):
            valid_rows.extend(
                [
                    round_events.iloc[i - 3 : i - 2],
                    round_events.iloc[i - 2 : i - 1],
                    round_events.iloc[i - 1 : i],
                    round_events.iloc[i : i + 1],
                ]
            )
    return pd.concat(valid_rows, ignore_index=True)


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


def apply_round_id_to_df(df: pd.DataFrame, round_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns a round id to each row in the DataFrame.

    Args:
        df (pd.DataFrame): A dataframe with a `tick` column.
        round_df (pd.DataFrame): A dataframe with the round data from `parse_demo`.

    Returns:
        pd.DataFrame: A dataframe with the round id assigned to column `round_id`.
    """
    if "tick" not in df.columns:
        tick_col_missing_msg = "DataFrame must contain a 'tick' column."
        raise KeyError(tick_col_missing_msg)
    interval_index = pd.IntervalIndex.from_arrays(
        round_df["round_start"], round_df["round_officially_ended"], closed="left"
    )
    intervals = pd.cut(df["tick"], interval_index)
    round_id_map = dict(zip(interval_index, round_df["round_id"], strict=True))
    df["round_id"] = intervals.map(round_id_map)
    return df[~df["round_id"].isna()]
