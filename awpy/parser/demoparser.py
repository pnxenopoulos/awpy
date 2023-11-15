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

import os
import warnings

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

from awpy.parser.enums import GameEvent, GameState, PlayerData, Team
from awpy.parser.models import Demo, DemoHeader\

from typing import Optional

def find_round_num(tick: int, rounds_df: pd.DataFrame) -> Optional[int]:
    for _, row in rounds_df.iterrows():
        if row['round_start'] <= tick <= row['round_end_official']:
            return int(row['round_num'])
    return None  # Return None or an appropriate value if no round is found

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
    return DemoHeader(**parsed_header)


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
    return create_round_df(round_event_df)


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

    final_df["round_num"] = range(1, len(final_df) + 1)
    final_df["round_end_official"] = final_df["round_end_official"].fillna(final_df["round_end"])

    return final_df


def parse_smokes_and_infernos(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the smokes and infernos of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with start/stops
            for infernos and smokes.

    Returns:
        pd.DataFrame: DataFrame with the parsed smokes and infernos data.
    """
    if len(parsed) == 0:
        warnings.warn("No smoke/inferno events found in the demofile.", stacklevel=2)
        return pd.DataFrame(columns=["entityid", "tick", "x", "y", "z", "event"])

    all_event_dfs = []

    for data in parsed:
        if len(data) == 0:
            continue

        key = data[0]
        parsed_df = data[1]
        parsed_df = parsed_df.loc[:, ["entityid", "tick", "x", "y", "z"]]
        parsed_df["event"] = key
        all_event_dfs.append(parsed_df)
    smoke_inferno_df = pd.concat(all_event_dfs)
    smoke_inferno_df.sort_values(by=["tick", "entityid"], inplace=True)

    return smoke_inferno_df


def parse_bomb_events(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the bomb events of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with bomb events.

    Returns:
        pd.DataFrame: DataFrame with the parsed bomb events data.
    """
    if len(parsed) == 0:
        warnings.warn("No bomb events found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=["tick", "event", "player", "steamid", "haskit", "site"]
        )

    all_event_dfs = []

    for data in parsed:
        if len(data) == 0:
            continue

        key = data[0]
        parsed_df = data[1]
        parsed_df["event"] = key
        parsed_df = parsed_df.rename(
            columns={"user_name": "player", "user_steamid": "steamid"}
        )
        match key:
            # No pickup or dropped. Might want to see if we can get player info on each
            case GameEvent.BOMB_PLANTED.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
            case GameEvent.BOMB_DEFUSED.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
            case GameEvent.BOMB_BEGINDEFUSE.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "haskit"]]
            case GameEvent.BOMB_BEGINPLANT.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
            case GameEvent.BOMB_EXPLODED.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
        all_event_dfs.append(parsed_df)

    bomb_df = pd.concat(all_event_dfs)
    bomb_df["steamid"] = bomb_df["steamid"].astype("Int64")

    bomb_df.sort_values(by=["tick"], inplace=True)

    return bomb_df


def parse_damages(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the damages of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with damage events.

    Returns:
        pd.DataFrame: DataFrame with the parsed damage events data.
    """
    if len(parsed) == 0:
        warnings.warn("No player damage events found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=[
                "armor",
                "attacker",
                "attacker_steamid",
                "dmg_armor",
                "dmg_health",
                "health",
                "hitgroup",
                "tick",
                "victim",
                "victim_steamid",
                "weapon",
            ]
        )

    damage_df = parsed[0][1]
    damage_df = damage_df.rename(
        columns={
            "attacker_name": "attacker",
            "user_name": "victim",
            "user_steamid": "victim_steamid",
        }
    )
    damage_df["attacker_steamid"] = damage_df["attacker_steamid"].astype("Int64")
    damage_df["victim_steamid"] = damage_df["victim_steamid"].astype("Int64")

    damage_df.sort_values(by=["tick"], inplace=True)

    return damage_df


def parse_blinds(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the blinds of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with blind events.

    Returns:
        pd.DataFrame: DataFrame with the parsed blind events data.
    """
    if len(parsed) == 0:
        warnings.warn("No player blind events found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=[
                "flasher",
                "flasher_steamid",
                "blind_duration",
                "entityid",
                "tick",
                "victim",
                "victim_steadid",
            ]
        )

    blind_df = parsed[0][1]
    blind_df = blind_df.rename(
        columns={
            "attacker_name": "flasher",
            "attacker_steamid": "flasher_steamid",
            "user_name": "victim",
            "user_steamid": "victim_steamid",
        }
    )
    blind_df["flasher_steamid"] = blind_df["flasher_steamid"].astype("Int64")
    blind_df["victim_steamid"] = blind_df["victim_steamid"].astype("Int64")

    blind_df.sort_values(by=["tick"], inplace=True)

    return blind_df


def parse_weapon_fires(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the weapon fires of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with
            weaponfire events.

    Returns:
        pd.DataFrame: DataFrame with the parsed weapon fire events data.
    """
    if len(parsed) == 0:
        warnings.warn("No weapon fires found in the demofile.", stacklevel=2)
        return pd.DataFrame(columns=["silenced", "tick", "player", "steamid", "weapon"])

    weapon_fires_df = parsed[0][1]
    weapon_fires_df = weapon_fires_df.rename(
        columns={
            "user_name": "player",
            "user_steamid": "steamid",
        }
    )
    weapon_fires_df["steamid"] = weapon_fires_df["steamid"].astype("Int64")

    weapon_fires_df.sort_values(by=["tick"], inplace=True)

    return weapon_fires_df


def parse_deaths(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the deaths of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with death events.

    Returns:
        pd.DataFrame: DataFrame with the parsed death events data.
    """
    if len(parsed) == 0:
        warnings.warn("No deaths found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=[
                "assistedflash",
                "assister_name",
                "assister_steamid",
                "attacker",
                "attacker_steamid",
                "attackerblind",
                "distance",
                "dmg_armor",
                "dmg_health",
                "dominated",
                "headshot",
                "hitgroup",
                "noreplay",
                "noscope",
                "penetrated",
                "revenge",
                "thrusmoke",
                "tick",
                "victim",
                "victim_steamid",
                "weapon",
                "weapon_fauxitemid",
                "weapon_itemid",
                "weapon_originalowner_xuid",
                "wipe",
            ]
        )

    death_df = parsed[0][1]
    death_df = death_df.rename(
        columns={
            "attacker_name": "attacker",
            "user_name": "victim",
            "user_steamid": "victim_steamid",
        }
    )
    death_df["attacker_steamid"] = death_df["attacker_steamid"].astype("Int64")
    death_df["assister_steamid"] = death_df["assister_steamid"].astype("Int64")
    death_df["victim_steamid"] = death_df["victim_steamid"].astype("Int64")

    death_df.sort_values(by=["tick"], inplace=True)

    return death_df


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
        [tick_df["team_num"] == Team.T.value, tick_df["team_num"] == Team.CT.value],
        ["t", "ct"],
        default="spectator",
    )
    tick_df["game_phase"] = tick_df["game_phase"].replace({
        0: "init",
        1: "pregame",
        2: "startgame",
        3: "preround",
        4: "teamwin",
        5: "restart",
        6: "stalemate",
        7: "gameover"
    })
    intersection = list(
        set(tick_df.columns).intersection(
            [
                "tick",
                "game_phase",
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

    tick_df["steamid"] = tick_df["steamid"].astype("Int64")

    return tick_df


def parse_demo(file: str) -> Demo:
    """Parse the demofile.

    Args:
        file (str): Path to the demofile.

    Returns:
        Demo: Dictionary with the parsed data. Has keys `header`, `rounds`, `kills`,
            `damages`, `effects`, `bomb_events`, `ticks`.
    """
    if not os.path.exists(file):
        err_msg = f"{file} not found."
        raise FileNotFoundError(err_msg)

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
    damage = parser.parse_events([GameEvent.PLAYER_HURT.value], other=["game_phase"])
    damage_df = parse_damages(damage)
    damage_df['round_num'] = damage_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
    damage_df["round_num"] = damage_df["round_num"].astype("Int64")

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
    effect_df['round_num'] = effect_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
    effect_df["round_num"] = effect_df["round_num"].astype("Int64")

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
    bomb_df['round_num'] = bomb_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
    bomb_df["round_num"] = bomb_df["round_num"].astype("Int64")

    # Deaths
    deaths = parser.parse_events(
        [
            GameEvent.PLAYER_DEATH.value,
        ],
    )
    death_df = parse_deaths(deaths)
    death_df['round_num'] = death_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
    death_df["round_num"] = death_df["round_num"].astype("Int64")

    # Blinds
    blinds = parser.parse_events([GameEvent.PLAYER_BLIND.value])
    blinds_df = parse_blinds(blinds)
    blinds_df['round_num'] = blinds_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
    blinds_df["round_num"] = blinds_df["round_num"].astype("Int64")

    # Weapon Fires
    weapon_fires = parser.parse_events([GameEvent.WEAPON_FIRE.value])
    weapon_fires_df = parse_weapon_fires(weapon_fires)
    weapon_fires_df['round_num'] = weapon_fires_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
    weapon_fires_df["round_num"] = weapon_fires_df["round_num"].astype("Int64")

    # Frames
    tick_df = pd.DataFrame(
        columns=[
            "tick",
            "game_phase",
            "side",
            "steamid",
            "in_buy_zone",
            "rank",
            "ping",
            "is_strafing",
            "Y",
            "player",
            "last_place",
            "in_bomb_zone",
            "X",
            "spotted",
            "is_walking",
            "active_weapon",
            "Z",
            "is_alive",
            "flash_duration",
            "health",
            "armor",
            "is_scoped",
            "in_crouch",
            "pitch",
            "is_defusing",
            "current_equip_value",
            "yaw",
            "clan",
            "flash_max_alpha",
            "round_start_equip_value",
        ]
    )
    try:
        tick_df = parser.parse_ticks(
            [
                GameState.GAME_PHASE.value,
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
                # Other
                GameState.TOTAL_ROUNDS_PLAYED.value
            ]
        )
        tick_df = parse_frame(tick_df)
    except Exception as err:
        warn_msg = f"Error parsing tick data found in the demofile: {err}"
        warnings.warn(warn_msg, stacklevel=2)

    # Grenades
    grenade_df = pd.DataFrame(
        columns=[
            "X",
            "Y",
            "Z",
            "tick",
            "thrower_steamid",
            "name",
            "grenade_type",
            "entity_id",
        ]
    )
    try:
        grenade_df = parser.parse_grenades()
        grenade_df['round_num'] = grenade_df['tick'].apply(lambda tick: find_round_num(tick, round_df))
        grenade_df["round_num"] = grenade_df["round_num"].astype("Int64")
    except Exception as err:
        warn_msg = f"Error parsing grenade data found in the demofile: {err}"
        warnings.warn(warn_msg, stacklevel=2)

    # Final dict
    parsed_data = {
        "header": header,
        "rounds": round_df,
        "kills": death_df,
        "damages": damage_df,
        "effects": effect_df,
        "bomb_events": bomb_df,
        "flashes": blinds_df,
        "weapon_fires": weapon_fires_df,
        "ticks": tick_df,
        "grenades": grenade_df,
    }

    return Demo(**parsed_data)
