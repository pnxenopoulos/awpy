"""Parsing methods for game frames."""

import numpy as np
import pandas as pd

from awpy.parser.enums import Side


def parse_frame(tick_df: pd.DataFrame) -> pd.DataFrame:
    """Parse the frame of the demofile.

    Args:
        tick_df (pd.DataFrame): DataFrame with the player-tick-level data.

    Returns:
        pd.DataFrame: DataFrame with the parsed player-tick-level data.
    """
    # Renaming columns
    rename_columns = {
        "name": "player",
        "clan_name": "clan",
        "last_place_name": "last_place",
    }
    tick_df = tick_df.rename(columns=rename_columns)

    # Updating 'side' based on 'team_num'
    tick_df["side"] = np.select(
        [tick_df["team_num"] == Side.T.value, tick_df["team_num"] == Side.CT.value],
        ["t", "ct"],
        default="spectator",
    )

    # Updating 'game_phase'
    game_phase_map = {
        0: "init",
        1: "pregame",
        2: "startgame",
        3: "preround",
        4: "teamwin",
        5: "restart",
        6: "stalemate",
        7: "gameover",
    }
    tick_df["game_phase"] = tick_df["game_phase"].replace(game_phase_map)

    # Selecting relevant columns
    relevant_columns = [
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
        "spotted",
    ]
    tick_df = tick_df[relevant_columns]

    # Converting 'steamid' to 'Int64'
    tick_df["steamid"] = tick_df["steamid"].astype("Int64")

    return tick_df


def create_empty_tick_df() -> pd.DataFrame:
    """Create an empty DataFrame with the columns of the tick DataFrame.

    Returns:
        pd.DataFrame: Empty DataFrame with the columns of the tick DataFrame.
    """
    columns = [
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
        "pitch",
        "is_defusing",
        "current_equip_value",
        "yaw",
        "clan",
        "flash_max_alpha",
        "round_start_equip_value",
    ]
    return pd.DataFrame(columns=columns)
