"""This module defines the DemoParser class that handles the core parsing functionality.

Core functionality is parsing and cleaning a Counter Strike demo file.

Example::

    from awpy.parser import parse_demo

    parsed = parse_demo("og-vs-natus-vincere-m1-dust2.dem")
    parsed["header"]
    parsed["rounds"]
    parsed["kills"]
    parsed["damages"]
    parsed["effects"]
    parsed["bomb_events"]
    parsed["ticks"]

https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb
"""

import pandas as pd
import numpy as np

from demoparser2 import DemoParser
from awpy.parser.models import Demo, DemoHeader
from awpy.parser.enums import GameEvent, PlayerData


def parse_header(parsed_header: dict) -> DemoHeader:
    """Parse the header of the demofile.

    Args:
        parsed_header (dict): The header of the demofile.

    Returns:
        DemoHeader: The parsed header of the demofile.
    """
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
    header = DemoHeader(**parsed_header)

    return header


def parse_rounds(parsed_round_events: list[tuple]) -> pd.DataFrame:
    """Parse the rounds of the demofile.

    Args:
        parsed_round_events (list[tuple]): Output of parser.parse_events(...)

    Returns:
        pd.DataFrame: Pandas DataFrame with the parsed rounds data.
    """
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
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
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
    parsed_rounds_df = create_round_df(round_event_df)

    return parsed_rounds_df


def create_round_df(round_event_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a DataFrame with the round events by matching start and end events.

    Args:
        round_event_df (pd.DataFrame): DataFrame with the round events.

    Returns:
        pd.DataFrame: DataFrame with the round events by matching start and end events.
    """
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

    return final_df


def parse_smokes_and_infernos(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the smokes and infernos of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with start/stop events for infernos and smokes.

    Returns:
        pd.DataFrame: DataFrame with the parsed smokes and infernos data.
    """
    parsed_dfs = []

    for data in parsed:
        key = data[0]
        df = data[1]
        df = df[["entityid", "tick", "x", "y", "z"]]
        df["event"] = key
        parsed_dfs.append(df)
    parsed_df = pd.concat(parsed_dfs)
    parsed_df = parsed_df.sort_values(by=["tick", "entityid"])

    return parsed_df


def parse_bomb_events(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the bomb events of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with bomb events.

    Returns:
        pd.DataFrame: DataFrame with the parsed bomb events data.
    """
    parsed_dfs = []

    for data in parsed:
        key = data[0]
        df = data[1]
        df["event"] = key
        df = df.rename(columns={"user_name": "player", "user_steamid": "steamid"})
        match key:
            # No pickup or dropped. Might want to see if we can get player info on each
            case GameEvent.BOMB_PLANTED.value:
                df = df[["tick", "event", "player", "steamid", "site"]]
            case GameEvent.BOMB_DEFUSED.value:
                df = df[["tick", "event", "player", "steamid", "site"]]
            case GameEvent.BOMB_BEGINDEFUSE.value:
                df = df[["tick", "event", "player", "steamid", "haskit"]]
            case GameEvent.BOMB_BEGINPLANT.value:
                df = df[["tick", "event", "player", "steamid", "site"]]
            case GameEvent.BOMB_EXPLODED.value:
                df = df[["tick", "event", "player", "steamid", "site"]]
        parsed_dfs.append(df)

    parsed_df = pd.concat(parsed_dfs)

    return parsed_df.sort_values(by=["tick"])


def parse_damages(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the damages of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with damage events.

    Returns:
        pd.DataFrame: DataFrame with the parsed damage events data.
    """
    damage_df = parsed[0][1]
    damage_df = damage_df.rename(
        columns={
            "attacker_name": "attacker",
            "user_name": "victim",
            "user_steamid": "victim_steamid",
        }
    )

    return damage_df.sort_values(by=["tick"])


def parse_deaths(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the deaths of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with death events.

    Returns:
        pd.DataFrame: DataFrame with the parsed death events data.
    """
    death_df = parsed[0][1]
    death_df = death_df.rename(
        columns={
            "attacker_name": "attacker",
            "user_name": "victim",
            "user_steamid": "victim_steamid",
        }
    )

    return death_df.sort_values(by=["tick"])


def parse_frame(tick_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the frame of the demofile.

    Args:
        tick_df (pd.DataFrame): DataFrame with the player-tick-level data.

    Returns:
        pd.DataFrame: DataFrame with the parsed player-tick-level data.
    """
    tick_df = tick_df.rename(
        columns={"name": "player", "clan_name": "clan", "last_place_name": "last_place"}
    )
    tick_df["side"] = np.select(
        [tick_df["team_num"] == 2.0, tick_df["team_num"] == 3.0],
        ["t", "ct"],
        default="spectator",
    )
    intersection = list(
        set(tick_df.columns).intersection(
            [
                "tick",
                "player",
                "steamid",
                "clan",
                "side",
                "X",
                "Y",
                "Z",
                "pitch",
                "yaw",
                "last_place",
                "is_alive",
                "health",
                "armor",
                "has_helmet",
                "has_defuser",
                "active_weapon",
                "current_equip_value",
                "round_start_equip_value",
                "rank",
                "ping",
                "flash_duration",
                "flash_max_alpha",
                "is_scoped",
                "is_defusing",
                "is_walking",
                "is_strafing",
                "in_buy_zone",
                "in_bomb_zone",
                "in_crouch",
                "spotted",
            ]
        )
    )
    tick_df = tick_df[intersection]

    return tick_df


def parse_demo(file: str) -> Demo:
    """Parse the demofile.

    Args:
        file (str): Path to the demofile.

    Returns:
        Demo: Dictionary with the parsed data. Has keys `header`, `rounds`, `kills`, `damages`, `effects`, `bomb_events`, `ticks`.
    """
    parser = DemoParser(file)

    # Header
    parsed_header = parser.parse_header()
    header = parse_header(parsed_header)

    # Rounds
    parsed_round_events = parser.parse_events(
        [
            GameEvent.ROUND_START.value,
            GameEvent.ROUND_FREEZE_END.value,
            GameEvent.BUYTIME_ENDED.value,
            GameEvent.ROUND_END.value,
            GameEvent.ROUND_OFFICIALLY_ENDED.value,
        ]
    )
    round_df = parse_rounds(parsed_round_events)

    # Damages
    damage = parser.parse_events([GameEvent.PLAYER_HURT.value])
    damage_df = parse_damages(damage)

    # Blockers (smokes, molotovs, etc.)
    effect = parser.parse_events(
        [
            GameEvent.INFERNO_STARTBURN.value,
            GameEvent.INFERNO_EXPIRE.value,
            GameEvent.SMOKEGRENADE_DETONATE.value,
            GameEvent.SMOKEGRENADE_EXPIRED.value,
        ]
    )
    effect_df = parse_smokes_and_infernos(effect)

    # Bomb
    bomb = parser.parse_events(
        [
            GameEvent.BOMB_BEGINDEFUSE.value,
            GameEvent.BOMB_BEGINPLANT.value,
            GameEvent.BOMB_DEFUSED.value,
            GameEvent.BOMB_EXPLODED.value,
            GameEvent.BOMB_PLANTED.value,
        ]
    )
    bomb_df = parse_bomb_events(bomb)

    # Deaths
    deaths = parser.parse_events(
        [
            GameEvent.PLAYER_DEATH.value,
        ]
    )
    death_df = parse_deaths(deaths)

    # Frames
    tick_df = parser.parse_ticks(
        [
            # Location
            PlayerData.X.value,
            PlayerData.Y.value,
            PlayerData.Z.value,
            PlayerData.PITCH.value,
            PlayerData.YAW.value,
            PlayerData.LAST_PLACE_NAME.value,
            # Health/Armor/Weapon
            PlayerData.IS_ALIVE.value,
            PlayerData.HEALTH.value,
            PlayerData.ARMOR.value,
            PlayerData.HAS_HELMET.value,
            PlayerData.HAS_DEFUSER.value,
            PlayerData.ACTIVE_WEAPON.value,
            PlayerData.CURRENT_EQUIP_VALUE.value,
            PlayerData.ROUND_START_EQUIP_VALUE.value,
            # Rank
            PlayerData.RANK.value,
            # Extra
            PlayerData.PING.value,
            PlayerData.CLAN_NAME.value,
            PlayerData.TEAM_NUM.value,
            PlayerData.FLASH_DURATION.value,
            PlayerData.FLASH_MAX_ALPHA.value,
            PlayerData.IS_SCOPED.value,
            PlayerData.IS_DEFUSING.value,
            PlayerData.IS_WALKING.value,
            PlayerData.IS_STRAFING.value,
            PlayerData.IN_BUY_ZONE.value,
            PlayerData.IN_BOMB_ZONE.value,
            PlayerData.IN_CROUCH.value,
            PlayerData.SPOTTED.value,
        ]
    )
    tick_df = parse_frame(tick_df)

    # Grenades
    grenade_df = parser.parse_grenades()

    # Final dict
    parsed_data = {
        "header": header,
        "rounds": round_df,
        "kills": death_df,
        "damages": damage_df,
        "effects": effect_df,
        "bomb_events": bomb_df,
        "ticks": tick_df,
        "grenades": grenade_df,
    }

    return parsed_data
