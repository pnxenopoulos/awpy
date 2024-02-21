"""Contains parsers for the different pieces of data."""

import numpy as np
import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611

from awpy.converters import (
    map_bombsites,
    map_hitgroup,
)


def remove_nonplay_ticks(parsed_df: pd.DataFrame) -> pd.DataFrame:
    """Filter out non-play records from a dataframe.

    Args:
        parsed_df (pd.DataFrame): A dataframe with the columns...

    Returns:
        pd.DataFrame: A dataframe with the non-play records removed.
    """
    # Check if the required columns are in the dataframe
    for col in [
        "is_freeze_period",
        "is_warmup_period",
        "is_terrorist_timeout",
        "is_ct_timeout",
        "is_technical_timeout",
        "is_waiting_for_resume",
        "is_match_started",
        "game_phase",
    ]:
        if col not in parsed_df.columns:
            error_msg = f"{col} not found in dataframe."
            raise ValueError(error_msg)

    # Remove records which do not occur in-play
    parsed_df = parsed_df[
        (~parsed_df["is_freeze_period"])
        & (~parsed_df["is_warmup_period"])
        & (~parsed_df["is_terrorist_timeout"])
        & (~parsed_df["is_ct_timeout"])
        & (~parsed_df["is_technical_timeout"])
        & (~parsed_df["is_waiting_for_resume"])
        & (parsed_df["is_match_started"])
        & (
            parsed_df["game_phase"].isin(
                [
                    2,  # startgame
                    3,  # preround
                ]
            )
        )
    ]

    # Drop the state columns
    return parsed_df.drop(
        columns=[
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ]
    )


def parse_grenades(parser: DemoParser) -> pd.DataFrame:
    """Parse the grenades of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The grenade trajectories for the demofile.
    """
    grenade_df = parser.parse_grenades()
    grenade_df = grenade_df.rename(columns={"name": "thrower"})
    return grenade_df[
        [
            "thrower_steamid",
            "thrower",
            "grenade_type",
            "tick",
            "X",
            "Y",
            "Z",
            "entity_id",
        ]
    ]


def parse_kills(parser: DemoParser) -> pd.DataFrame:
    """Parse the kills of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The kills for the demofile.
    """
    # Parse the kills from the demoparser
    kill_df = parser.parse_event(
        "player_death",
        player=[
            "X",
            "Y",
            "Z",
            "last_place_name",
            "health",
            "armor",
            "inventory",
            "current_equip_value",
            "rank",
            "ping",
            "has_defuser",
            "has_helmet",
            "pitch",
            "yaw",
            "team_name",
        ],
        other=[
            "is_bomb_planted",
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )

    # Filter out nonplay ticks
    kill_df = remove_nonplay_ticks(kill_df)

    # Get only relevant columns
    kill_df = kill_df[
        [
            # Kill Info
            "tick",
            "assistedflash",
            "dmg_health",
            "dmg_armor",
            "attackerblind",
            "headshot",
            "hitgroup",
            "noscope",
            "penetrated",
            "thrusmoke",
            "is_bomb_planted",
            # Assister
            "assister_X",
            "assister_Y",
            "assister_Z",
            "assister_pitch",
            "assister_yaw",
            "assister_last_place_name",
            "assister_health",
            "assister_armor",
            "assister_current_equip_value",
            "assister_has_defuser",
            "assister_has_helmet",
            "assister_inventory",
            "assister_ping",
            "assister_pitch",
            "assister_team_name",
            "assister_name",
            "assister_steamid",
            # Attacker
            "attacker_X",
            "attacker_Y",
            "attacker_Z",
            "attacker_pitch",
            "attacker_yaw",
            "attacker_last_place_name",
            "attacker_health",
            "attacker_armor",
            "attacker_current_equip_value",
            "attacker_has_defuser",
            "attacker_has_helmet",
            "attacker_inventory",
            "attacker_ping",
            "attacker_pitch",
            "attacker_team_name",
            "attacker_name",
            "attacker_steamid",
            # Victim
            "user_X",
            "user_Y",
            "user_Z",
            "user_pitch",
            "user_yaw",
            "user_last_place_name",
            "user_health",
            "user_armor",
            "user_current_equip_value",
            "user_has_defuser",
            "user_has_helmet",
            "user_inventory",
            "user_ping",
            "user_pitch",
            "user_team_name",
            "user_name",
        ]
    ]

    # Rename columns
    kill_df = kill_df.rename(
        columns={
            "is_bomb_planted": "bomb_planted",
            "assister_team_name": "assister_side",
            "attacker_team_name": "attacker_side",
            "user_team_name": "victim_side",
            "assister_last_place_name": "assister_place",
            "attacker_last_place_name": "attacker_place",
            "user_last_place_name": "victim_place",
            "assister_has_defuser": "assister_defuser",
            "attacker_has_defuser": "attacker_defuser",
            "user_has_defuser": "victim_defuser",
            "assister_has_helmet": "assister_helmet",
            "attacker_has_helmet": "attacker_helmet",
            "user_has_helmet": "victim_helmet",
            "assister_current_equip_value": "assister_equipment_value",
            "attacker_current_equip_value": "attacker_equipment_value",
            "user_current_equip_value": "victim_equipment_value",
        }
    )
    for col in kill_df.columns:
        if "user_" in col:
            kill_df = kill_df.rename(columns={col: col.replace("user_", "victim_")})

    # Convert hitgroup to string
    kill_df["hitgroup"] = map_hitgroup(kill_df["hitgroup"])

    return kill_df


def parse_damages(parser: DemoParser) -> pd.DataFrame:
    """Parse the damages of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The damages for the demofile.
    """
    # Parse the damages from the demoparser
    damage_df = parser.parse_event(
        "player_hurt",
        player=[
            "X",
            "Y",
            "Z",
            "last_place_name",
            "health",
            "armor",
            "inventory",
            "current_equip_value",
            "rank",
            "ping",
            "has_defuser",
            "has_helmet",
            "pitch",
            "yaw",
            "team_name",
        ],
        other=[
            "is_bomb_planted",
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )

    # Filter out nonplay ticks
    damage_df = remove_nonplay_ticks(damage_df)

    # Get only relevant columns
    damage_df = damage_df[
        [
            # Damage info
            "tick",
            "weapon",
            "dmg_armor",
            "dmg_health",
            "hitgroup",
            "is_bomb_planted",
            # Attacker
            "attacker_X",
            "attacker_Y",
            "attacker_Z",
            "attacker_pitch",
            "attacker_yaw",
            "attacker_last_place_name",
            "attacker_health",
            "attacker_armor",
            "attacker_current_equip_value",
            "attacker_has_defuser",
            "attacker_has_helmet",
            "attacker_inventory",
            "attacker_ping",
            "attacker_pitch",
            "attacker_team_name",
            "attacker_name",
            "attacker_steamid",
            # Victim
            "user_X",
            "user_Y",
            "user_Z",
            "user_pitch",
            "user_yaw",
            "user_last_place_name",
            "user_health",
            "user_armor",
            "user_current_equip_value",
            "user_has_defuser",
            "user_has_helmet",
            "user_inventory",
            "user_ping",
            "user_pitch",
            "user_team_name",
            "user_name",
        ]
    ]

    # Rename columns
    damage_df = damage_df.rename(
        columns={
            "is_warmup_period": "warmup",
            "is_match_started": "started",
            "is_bomb_planted": "bomb_planted",
            "game_phase": "phase",
            "attacker_team_name": "attacker_side",
            "user_team_name": "victim_side",
            "attacker_last_place_name": "attacker_place",
            "user_last_place_name": "victim_place",
            "attacker_has_defuser": "attacker_defuser",
            "user_has_defuser": "victim_defuser",
            "attacker_has_helmet": "attacker_helmet",
            "user_has_helmet": "victim_helmet",
            "attacker_current_equip_value": "attacker_equipment_value",
            "user_current_equip_value": "victim_equipment_value",
        }
    )

    for col in damage_df.columns:
        if "user_" in col:
            damage_df = damage_df.rename(columns={col: col.replace("user_", "victim_")})

    # Convert hitgroup to string
    damage_df["hitgroup"] = map_hitgroup(damage_df["hitgroup"])

    # Create dmg_health_real column
    damage_df["dmg_health_real"] = np.where(
        damage_df["dmg_health"] > damage_df["victim_health"],
        damage_df["victim_health"],
        damage_df["dmg_health"],
    )

    return damage_df


def parse_bomb(parser: DemoParser) -> pd.DataFrame:
    """Parse the bomb events of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The bomb events for the demofile.
    """
    # Get bomb plants
    bomb_planted = parser.parse_event(
        "bomb_planted",
        player=["X", "Y", "Z"],
        other=[
            "which_bomb_zone",
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    bomb_planted["event"] = "planted"
    bomb_planted = remove_nonplay_ticks(bomb_planted)
    # Get bomb defuses
    bomb_defused = parser.parse_event(
        "bomb_defused",
        player=["X", "Y", "Z"],
        other=[
            "which_bomb_zone",
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    bomb_defused["event"] = "defused"
    bomb_defused = remove_nonplay_ticks(bomb_defused)
    # Get bomb explosions
    bomb_exploded = parser.parse_event(
        "bomb_exploded",
        player=["X", "Y", "Z"],
        other=[
            "which_bomb_zone",
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    bomb_exploded["event"] = "exploded"
    bomb_exploded = remove_nonplay_ticks(bomb_exploded)
    # Combine all bomb events
    bomb_df = pd.concat([bomb_planted, bomb_defused, bomb_exploded])
    bomb_df["site"] = map_bombsites(bomb_df["site"])
    # Rename columns
    for col in bomb_df.columns:
        if "user_" in col:
            bomb_df = bomb_df.rename(columns={col: col.replace("user_", "player_")})
    return bomb_df


def parse_smokes(parser: DemoParser) -> pd.DataFrame:
    """Parse the smokes of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The smokes for the demofile.
    """
    # Get smoke starts
    smoke_starts = parser.parse_event(
        "smokegrenade_detonate",
        player=["team_name"],
        other=[
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    smoke_starts = remove_nonplay_ticks(smoke_starts)
    # Get smoke ends
    smoke_ends = parser.parse_event(
        "smokegrenade_expired",
        other=[
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    smoke_ends = remove_nonplay_ticks(smoke_ends)
    # Initialize an empty list to store the matched rows
    matched_rows = []
    # Loop through each row in smoke starts
    for _, start_row in smoke_starts.iterrows():
        # Find the corresponding end row
        end_row = smoke_ends[
            (smoke_ends["entityid"] == start_row["entityid"])
            & (smoke_ends["tick"] > start_row["tick"])
        ]
        combined_row = {
            "entity_id": start_row["entityid"],
            "start_tick": start_row["tick"],
            "end_tick": None if end_row.empty else end_row.iloc[0]["tick"],
            "thrower_name": start_row["user_name"],
            "thrower_steamid": start_row["user_steamid"],
            "X": start_row["x"],
            "Y": start_row["y"],
            "Z": start_row["z"],
        }
        matched_rows.append(combined_row)
    return pd.DataFrame(matched_rows)


def parse_flashes(parser: DemoParser) -> pd.DataFrame:
    """Parse the flashes of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The flashes for the demofile.
    """
    blind_df = parser.parse_event(
        "player_blind",
        player=["X", "Y", "Z", "last_place_name", "pitch", "yaw", "team_name"],
        other=[
            "is_bomb_planted",
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    blind_df = remove_nonplay_ticks(blind_df)
    blind_df = blind_df[
        [
            "tick",
            "entityid",
            "blind_duration",
            "attacker_name",
            "attacker_steamid",
            "attacker_team_name",
            "attacker_X",
            "attacker_Y",
            "attacker_Z",
            "attacker_last_place_name",
            "attacker_pitch",
            "attacker_yaw",
            "user_name",
            "user_steamid",
            "user_team_name",
            "user_X",
            "user_Y",
            "user_Z",
            "user_last_place_name",
            "user_pitch",
            "user_yaw",
            "is_bomb_planted",
        ]
    ]
    return blind_df.rename(
        columns={
            "entityid": "entity_id",
            "is_warmup_period": "warmup",
            "is_match_started": "started",
            "is_bomb_planted": "bomb_planted",
            "game_phase": "phase",
            "attacker_team_name": "attacker_side",
            "user_team_name": "victim_side",
            "attacker_last_place_name": "attacker_place",
            "user_last_place_name": "victim_place",
        }
    )


def parse_infernos(parser: DemoParser) -> pd.DataFrame:
    """Parse the infernos of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The infernos for the demofile.
    """
    inferno_starts = parser.parse_event(
        "inferno_startburn",
        other=[
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    inferno_starts = remove_nonplay_ticks(inferno_starts)
    inferno_ends = parser.parse_event(
        "inferno_expire",
        other=[
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    inferno_ends = remove_nonplay_ticks(inferno_ends)
    # Initialize an empty list to store the matched rows
    matched_rows = []
    # Loop through each row in inferno_starts
    for _, start_row in inferno_starts.iterrows():
        # Find the corresponding end row
        end_row = inferno_ends[
            (inferno_ends["entityid"] == start_row["entityid"])
            & (inferno_ends["tick"] > start_row["tick"])
        ]
        # If a match is found, append the combined data to the matched_rows list
        combined_row = {
            "entity_id": start_row["entityid"],
            "start_tick": start_row["tick"],
            "end_tick": None if end_row.empty else end_row.iloc[0]["tick"],
            "thrower_name": start_row["user_name"],
            "thrower_steamid": start_row["user_steamid"],
            "X": start_row["x"],
            "Y": start_row["y"],
            "Z": start_row["z"],
        }
        matched_rows.append(combined_row)
    return pd.DataFrame(matched_rows)


def parse_weapon_fires(parser: DemoParser) -> pd.DataFrame:
    """Parse the weapon fires of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The weapon fires for the demofile.
    """
    weapon_fires_df = parser.parse_event(
        "weapon_fire",
        player=[
            "X",
            "Y",
            "Z",
            "last_place_name",
            "health",
            "armor",
            "inventory",
            "current_equip_value",
            "rank",
            "ping",
            "has_defuser",
            "has_helmet",
            "pitch",
            "yaw",
            "team_name",
            "accuracy_penalty",
            "is_strafing",
            "zoom_lvl",
            "last_shot_time",
            "fire_seq_start_time",
        ],
        other=[
            # State
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ],
    )
    weapon_fires_df = remove_nonplay_ticks(weapon_fires_df)
    weapon_fires_df = weapon_fires_df[
        [
            "tick",
            "user_name",
            "user_steamid",
            "user_team_name",
            "user_X",
            "user_Y",
            "user_Z",
            "user_yaw",
            "user_pitch",
            "user_last_place_name",
            "user_is_strafing",
            "user_accuracy_penalty",
            "user_health",
            "user_armor",
            "user_rank",
            "user_zoom_lvl",
            "user_inventory",
            "weapon",
        ]
    ]
    weapon_fires_df.rename(columns={"user_last_place_name": "player_place"})
    for col in weapon_fires_df.columns:
        if "user_" in col:
            weapon_fires_df = weapon_fires_df.rename(
                columns={col: col.replace("user_", "player_")}
            )
    return weapon_fires_df


def parse_ticks(parser: DemoParser) -> pd.DataFrame:
    """Parse the ticks of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The ticks for the demofile.
    """
    ticks = parser.parse_ticks(
        [
            # Key presses
            "FORWARD",
            "LEFT",
            "RIGHT",
            "BACK",
            "FIRE",
            "RIGHTCLICK",
            "RELOAD",
            "INSPECT",
            "USE",
            "ZOOM",
            "SCOREBOARD",
            "WALK",
            # Player
            "team_name",
            "X",
            "Y",
            "Z",
            "pitch",
            "yaw",
            "last_place_name",
            "is_walking",
            "is_strafing",
            "in_crouch",
            "health",
            "armor",
            "has_defuser",
            "has_helmet",
            "inventory",
            "current_equip_value",
            "active_weapon",
            "rank",
            "ping",
            # Game State
            "is_bomb_planted",
            # State for filtering
            "is_freeze_period",
            "is_warmup_period",
            "is_terrorist_timeout",
            "is_ct_timeout",
            "is_technical_timeout",
            "is_waiting_for_resume",
            "is_match_started",
            "game_phase",
        ]
    )
    ticks = remove_nonplay_ticks(ticks)
    return ticks.rename(
        columns={
            "FORWARD": "key_forward",
            "LEFT": "key_left",
            "RIGHT": "key_right",
            "BACK": "key_back",
            "FIRE": "key_fire",
            "RIGHTCLICK": "key_rightclick",
            "RELOAD": "key_reload",
            "INSPECT": "key_inspect",
            "USE": "key_use",
            "ZOOM": "key_zoom",
            "SCOREBOARD": "key_scoreboard",
            "WALK": "key_walk",
            "active_weapon": "weapon",
            "last_place_name": "place",
            "team_name": "side",
        }
    )
