"""This module defines the DemoParser class that handles the core parsing functionality.

Core functionality is parsing and cleaning a Counter Strike demo file.

Example::

    from awpy.parser import parse_demo

    parsed = parse_demo(file="og-vs-natus-vincere-m1-dust2.dem")
    parsed.header
    parsed.events
    parsed.ticks
    parsed.grenades

https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb
"""

import os
import warnings

import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611

from awpy.parser.enums import Button, GameEvent, GameState, PlayerData
from awpy.parser.header import parse_header
from awpy.parser.models import Demo


def build_event_list(*, extended_events: bool = False) -> list[str]:
    """Build the list of events to parse.

    Args:
        extended_events (bool, optional): Whether to parse an extended
            set of events. Defaults to False.

    Returns:
        list[str]: List of events to parse, see `GameEvent` enum.
    """
    events = [
        # Round
        GameEvent.ROUND_START.value,
        GameEvent.ROUND_FREEZE_END.value,
        GameEvent.ROUND_END.value,
        GameEvent.ROUND_OFFICIALLY_ENDED.value,
        # Bomb
        GameEvent.BOMB_PLANTED.value,
        GameEvent.BOMB_DEFUSED.value,
        GameEvent.BOMB_BEGINPLANT.value,
        GameEvent.BOMB_EXPLODED.value,
        GameEvent.BOMB_BEGINDEFUSE.value,
        # Grenade
        GameEvent.FLASHBANG_DETONATE.value,
        GameEvent.HEGRENADE_DETONATE.value,
        GameEvent.INFERNO_STARTBURN.value,
        GameEvent.INFERNO_EXPIRE.value,
        GameEvent.SMOKEGRENADE_DETONATE.value,
        GameEvent.SMOKEGRENADE_EXPIRED.value,
        # Player
        GameEvent.PLAYER_HURT.value,
        GameEvent.PLAYER_DEATH.value,
        # Phases
        GameEvent.BEGIN_NEW_MATCH.value,
        GameEvent.ANNOUNCE_PHASE_END.value,
        GameEvent.ROUND_ANNOUNCE_LAST_ROUND_HALF.value,
        GameEvent.ROUND_ANNOUNCE_MATCH_START.value,
    ]
    if extended_events:
        events.extend(
            [
                GameEvent.DECOY_STARTED.value,
                GameEvent.DECOY_DETONATE.value,
                GameEvent.BOMB_DROPPED.value,
                GameEvent.BOMB_PICKUP.value,
                GameEvent.PLAYER_CONNECT.value,
                GameEvent.PLAYER_DISCONNECT.value,
                GameEvent.PLAYER_JUMP.value,
                GameEvent.PLAYER_FOOTSTEP.value,
                GameEvent.WEAPON_FIRE.value,
                GameEvent.WEAPON_RELOAD.value,
                GameEvent.WEAPON_ZOOM.value,
                GameEvent.ITEM_EQUIP.value,
                GameEvent.ROUND_MVP.value,
                GameEvent.RANK_UPDATE.value,
            ]
        )
    return events


def parse_events_from_demo(
    parser: DemoParser, event_list: list[str]
) -> list[tuple[str, pd.DataFrame]]:
    """Get events from the `demoparser2` Rust-based parser.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        event_list (list[str]): List of events to parse, see `GameEvent` enum.

    Returns:
        list[Tuple[str, pd.DataFrame]]: List of tuples containing the event name
            and the parsed event data.
    """
    try:
        return parser.parse_events(event_list)
    except Exception as err:
        warnings.warn(f"Error parsing events: {err}", stacklevel=2)
        return []


def parse_ticks_from_demo(parser: DemoParser, properties: list[str]) -> pd.DataFrame:
    """Parse the ticks of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.
        properties (list[str]): List of properties to parse, see `GameState` and
            `PlayerData` enums.

    Returns:
        pd.DataFrame: DataFrame with the parsed tick data.
    """
    tick_df = create_empty_df(properties)
    try:
        tick_df = parser.parse_ticks(properties)
    except Exception as err:
        warnings.warn(f"Error parsing tick data: {err}", stacklevel=2)
    return tick_df


def build_tick_properties(*, extended_ticks: bool, keystrokes: bool) -> list[str]:
    """Build the properties to parse for ticks.

    Args:
        extended_ticks (bool): Whether to parse extended tick information.
        keystrokes (bool): Whether to parse keystrokes.

    Returns:
        list[str]: List of properties to parse, see `GameState` and `PlayerData` enums.
    """
    properties = [
        GameState.GAME_PHASE.value,
        PlayerData.TEAM_NUM.value,
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
        # Misc
        PlayerData.PING.value,
    ]
    if extended_ticks:
        properties.extend(
            [
                PlayerData.RANK.value,
                PlayerData.FLASH_DURATION.value,
                PlayerData.FLASH_MAX_ALPHA.value,
                PlayerData.IS_SCOPED.value,
                PlayerData.IS_DEFUSING.value,
                PlayerData.IS_WALKING.value,
                PlayerData.IS_STRAFING.value,
                PlayerData.IN_BUY_ZONE.value,
                PlayerData.IN_BOMB_ZONE.value,
                PlayerData.SPOTTED.value,
                PlayerData.WHICH_BOMB_ZONE.value,
            ]
        )
    if keystrokes:
        properties.extend(
            [
                Button.FORWARD.value,
                Button.BACK.value,
                Button.LEFT.value,
                Button.RIGHT.value,
                Button.FIRE.value,
                Button.RIGHTCLICK.value,
                Button.RELOAD.value,
                Button.WALK.value,
                Button.ZOOM.value,
                Button.SCOREBOARD.value,
            ]
        )
    return properties


def create_empty_df(columns: list[str]) -> pd.DataFrame:
    """Create an empty DataFrame with the given columns.

    Args:
        columns (list[str]): List of column names.

    Returns:
        pd.DataFrame: Empty DataFrame with the given columns.
    """
    return pd.DataFrame(columns=columns)


def parse_grenades_from_demo(parser: DemoParser) -> pd.DataFrame:
    """Parse the grenades of the demofile.

    Args:
        parser (DemoParser): The `demoparser2` Rust-based parser.

    Returns:
        pd.DataFrame: DataFrame with the parsed grenade data.
    """
    grenade_df = create_empty_df(
        ["X", "Y", "Z", "tick", "thrower_steamid", "name", "grenade_type", "entity_id"]
    )
    try:
        return parser.parse_grenades()
    except Exception as err:
        warnings.warn(f"Error parsing grenade data: {err}", stacklevel=2)
    return grenade_df


def parse_demo(
    *,
    file: str,
    ticks: bool = True,
    extended_ticks: bool = False,
    extended_events: bool = False,
    keystrokes: bool = False,
) -> Demo:
    """Parse a Counter-Strike 2 demo file.

    Args:
        file (str): Path to the demo file.
        ticks (bool, optional): Whether to parse ticks. Defaults to True.
        extended_ticks (bool, optional): Whether to parse extended information
            for each tick. Defaults to False.
        extended_events (bool, optional): Whether to parse extended
            events. Defaults to False.
        keystrokes (bool, optional): Whether to parse keystrokes. Defaults to False.

    Raises:
        FileNotFoundError: If the filepath does not exist.

    Returns:
        Demo: A `Demo` object containing the parsed data.
    """
    if not os.path.exists(file):
        file_not_found_msg = f"{file} not found."
        raise FileNotFoundError(file_not_found_msg)

    if extended_ticks and not ticks:
        warnings.warn(
            "Extended ticks set to TRUE but ticks is set to FALSE. Defaulting to both.",
            stacklevel=2,
        )

    # Create a parser object
    parser = DemoParser(file)

    # Parse all relevant events
    event_list = build_event_list(extended_events=extended_events)
    parsed_events = parse_events_from_demo(
        parser,
        event_list,
    )
    events: dict[str, pd.DataFrame] = dict(parsed_events)

    # Parse relevant
    parsed_ticks = None
    if ticks:
        props = build_tick_properties(
            extended_ticks=extended_ticks, keystrokes=keystrokes
        )
        parsed_ticks = parse_ticks_from_demo(
            parser,
            props,
        )

    # Parse grenades
    parsed_grenades = parse_grenades_from_demo(parser)

    # Parse the demo header
    header = parse_header(parser.parse_header())

    # Create the parsed demo response
    return Demo(
        header=header, events=events, ticks=parsed_ticks, grenades=parsed_grenades
    )
