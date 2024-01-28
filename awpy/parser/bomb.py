"""Parsing methods for bomb-related events."""

import warnings
import pandas as pd

from awpy.parser.enums import GameEvent


def parse_bomb_events(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the bomb events of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with bomb events.

    Returns:
        pd.DataFrame: DataFrame with the parsed bomb events data.
    """
    if not parsed:
        warnings.warn("No bomb events found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=["tick", "event", "player", "steamid", "haskit", "site"]
        )

    all_event_dfs = [
        process_bomb_event_type(key, df) for key, df in parsed if not df.empty
    ]

    bomb_df = pd.concat(all_event_dfs)
    bomb_df["steamid"] = bomb_df["steamid"].astype("Int64")
    return bomb_df.sort_values(by=["tick"])


def process_bomb_event_type(key: str, df: pd.DataFrame) -> pd.DataFrame:
    """Process a bomb event type (bomb plant, defusal, etc.).

    Args:
        key (str): The event type. One of the `GameEvent` enums for bomb-related events.
        df (pd.DataFrame): The DataFrame containing the bomb event data.

    Returns:
        pd.DataFrame: The processed DataFrame containing all instances of the
            specified event type.
    """
    df["event"] = key
    df = df.rename(columns={"user_name": "player", "user_steamid": "steamid"})

    columns_map = {
        GameEvent.BOMB_PLANTED.value: ["tick", "event", "player", "steamid", "site"],
        GameEvent.BOMB_DEFUSED.value: ["tick", "event", "player", "steamid", "site"],
        GameEvent.BOMB_BEGINDEFUSE.value: [
            "tick",
            "event",
            "player",
            "steamid",
            "haskit",
        ],
        GameEvent.BOMB_BEGINPLANT.value: ["tick", "event", "player", "steamid", "site"],
        GameEvent.BOMB_EXPLODED.value: ["tick", "event", "player", "steamid", "site"],
    }

    return df[columns_map.get(key, [])]
