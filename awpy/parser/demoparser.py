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

from awpy.parser.bomb import parse_bomb_events
from awpy.parser.damage import (
    add_trade_info,
    parse_damages,
    parse_deaths,
)
from awpy.parser.enums import GameEvent, GameState, PlayerData
from awpy.parser.frame import create_empty_tick_df, parse_frame
from awpy.parser.grenade import parse_blinds, parse_smokes_and_infernos
from awpy.parser.header import parse_header
from awpy.parser.models import Demo
from awpy.parser.round import apply_round_num_to_df, parse_rounds_df
from awpy.parser.weapon import parse_weapon_fires


def get_events_from_parser(parser: DemoParser, event_list: list[str]) -> list[tuple]:
    """Get events from the `demoparser2` Rust-based parser.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        event_list (list[str]): List of events to parse, see `GameEvent` enum.

    Returns:
        list[tuple]: List of tuples containing the event name and the parsed event data.
    """
    try:
        return parser.parse_events(event_list)
    except Exception as err:
        warnings.warn(f"Error parsing events: {err}", stacklevel=2)
        return []


def parse_effects_df(parser: DemoParser, round_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the effects (infernos, smokes) of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.

    Returns:
        pd.DataFrame: DataFrame with the parsed effects data.
    """
    effects = get_events_from_parser(
        parser,
        [
            GameEvent.INFERNO_STARTBURN.value,
            GameEvent.INFERNO_EXPIRE.value,
            GameEvent.SMOKEGRENADE_DETONATE.value,
            GameEvent.SMOKEGRENADE_EXPIRED.value,
        ],
    )
    effects_df = parse_smokes_and_infernos(effects)
    return apply_round_num_to_df(effects_df, round_df)


def parse_damages_df(
    parser: DemoParser, round_df: pd.DataFrame, tick_df: pd.DataFrame
) -> pd.DataFrame:
    """Parse the damages of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.
        tick_df (pd.DataFrame): DataFrame containing the parsed tick data.

    Returns:
        pd.DataFrame: DataFrame with the parsed damage data.
    """
    damages = get_events_from_parser(parser, [GameEvent.PLAYER_HURT.value])
    damage_df = parse_damages(damages)

    # Add attacker side
    damage_df = damage_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "attacker_steamid"],
        right_on=["tick", "steamid"],
    )
    damage_df = damage_df.drop("steamid", axis=1)
    damage_df = damage_df.rename(columns={"side": "attacker_side"})

    # Add victim side
    damage_df = damage_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "victim_steamid"],
        right_on=["tick", "steamid"],
    )
    damage_df = damage_df.drop("steamid", axis=1)
    damage_df = damage_df.rename(columns={"side": "victim_side"})

    return apply_round_num_to_df(damage_df, round_df)


def parse_bomb_events_df(parser: DemoParser, round_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the bomb events of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.

    Returns:
        pd.DataFrame: DataFrame with the parsed bomb events data.
    """
    bomb_events = get_events_from_parser(
        parser,
        [
            GameEvent.BOMB_BEGINDEFUSE.value,
            GameEvent.BOMB_BEGINPLANT.value,
            GameEvent.BOMB_DEFUSED.value,
            GameEvent.BOMB_EXPLODED.value,
            GameEvent.BOMB_PLANTED.value,
        ],
    )
    bomb_df = parse_bomb_events(bomb_events)
    return apply_round_num_to_df(bomb_df, round_df)


def parse_kills_df(
    parser: DemoParser, round_df: pd.DataFrame, tick_df: pd.DataFrame, trade_time: int
) -> pd.DataFrame:
    """Parse the kills of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.
        tick_df (pd.DataFrame): DataFrame containing the parsed tick data.
        trade_time (int): Ticks between trade kills.

    Returns:
        pd.DataFrame: DataFrame with the parsed kill data.
    """
    kills = get_events_from_parser(parser, [GameEvent.PLAYER_DEATH.value])
    kill_df = parse_deaths(kills)
    kill_df = apply_round_num_to_df(kill_df, round_df)

    # Add attacker side
    kill_df = kill_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "attacker_steamid"],
        right_on=["tick", "steamid"],
        how="left",
    )
    kill_df = kill_df.drop("steamid", axis=1)
    kill_df = kill_df.rename(columns={"side": "attacker_side"})
    kill_df["attacker_side"] = kill_df["attacker_side"].replace([np.nan], [None])

    # Add victim side
    kill_df = kill_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "victim_steamid"],
        right_on=["tick", "steamid"],
        how="left",
    )
    kill_df = kill_df.drop("steamid", axis=1)
    kill_df = kill_df.rename(columns={"side": "victim_side"})
    kill_df["victim_side"] = kill_df["victim_side"].replace([np.nan], [None])

    # Add assister side
    kill_df = kill_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "assister_steamid"],
        right_on=["tick", "steamid"],
        how="left",
    )
    kill_df = kill_df.drop("steamid", axis=1)
    kill_df = kill_df.rename(columns={"side": "assister_side"})
    kill_df["assister_side"] = kill_df["assister_side"].replace([np.nan], [None])

    # Add trade info (must be done after adding sides)
    return add_trade_info(kill_df, trade_time)


def parse_blinds_df(parser: DemoParser, round_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the blinds of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.

    Returns:
        pd.DataFrame: DataFrame with the parsed blind data.
    """
    blinds = get_events_from_parser(parser, [GameEvent.PLAYER_BLIND.value])
    blinds_df = parse_blinds(blinds)
    return apply_round_num_to_df(blinds_df, round_df)


def parse_weapon_fires_df(parser: DemoParser, round_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the weapon fires of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.

    Returns:
        pd.DataFrame: DataFrame with the parsed weapon fires data.
    """
    weapon_fires = get_events_from_parser(parser, [GameEvent.WEAPON_FIRE.value])
    weapon_fires_df = parse_weapon_fires(weapon_fires)
    return apply_round_num_to_df(weapon_fires_df, round_df)


def parse_grenades_df(parser: DemoParser, round_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the grenades of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.

    Returns:
        pd.DataFrame: DataFrame with the parsed grenade data.
    """
    try:
        grenade_df = parser.parse_grenades()
        return apply_round_num_to_df(grenade_df, round_df)
    except Exception as err:
        warnings.warn(f"Error parsing grenade data: {err}", stacklevel=2)
        return pd.DataFrame()


def parse_ticks_df(parser: DemoParser, round_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the ticks of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        round_df (pd.DataFrame): DataFrame containing the parsed rounds data.

    Returns:
        pd.DataFrame: DataFrame with the parsed tick data.
    """
    tick_df = create_empty_tick_df()
    try:
        tick_df = apply_round_num_to_df(
            parse_frame(
                parser.parse_ticks(
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
                        PlayerData.SPOTTED.value,
                    ]
                )
            ),
            round_df,
        )
    except Exception as err:
        warnings.warn(f"Error parsing tick data: {err}", stacklevel=2)
    return tick_df


def parse_demo(file: str, trade_time: int = 640) -> Demo:
    """Parse a Counter-Strike 2 demo file.

    Args:
        file (str): Path to the demo file.
        trade_time (int, optional): Maximum time between trade kills in
            ticks. Defaults to 640.

    Raises:
        FileNotFoundError: If the filepath does not exist.

    Returns:
        Demo: A `Demo` object containing the parsed data.
    """
    if not os.path.exists(file):
        file_not_found_msg = f"{file} not found."
        raise FileNotFoundError(file_not_found_msg)

    parser = DemoParser(file)

    # Parse the rounds
    round_events = get_events_from_parser(
        parser,
        [
            GameEvent.ROUND_START.value,
            GameEvent.ROUND_FREEZE_END.value,
            GameEvent.BUYTIME_ENDED.value,
            GameEvent.ROUND_END.value,
            GameEvent.ROUND_OFFICIALLY_ENDED.value,
        ],
    )
    rounds_df = parse_rounds_df(round_events)
    ticks_df = parse_ticks_df(parser, rounds_df)
    parsed_data = {
        "header": parse_header(parser.parse_header()),
        "rounds": rounds_df,
        "ticks": ticks_df,
        "effects": parse_effects_df(parser, rounds_df),
        "damages": parse_damages_df(parser, rounds_df, ticks_df),
        "bomb_events": parse_bomb_events_df(parser, rounds_df),
        "kills": parse_kills_df(parser, rounds_df, ticks_df, trade_time),
        "flashes": parse_blinds_df(parser, rounds_df),
        "weapon_fires": parse_weapon_fires_df(parser, rounds_df),
        "grenades": parse_grenades_df(parser, rounds_df),
    }

    return Demo(**parsed_data)
