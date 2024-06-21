"""Contains parsers for the different pieces of data."""

import numpy as np
import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611
from loguru import logger

from awpy.converters import (
    map_hitgroup,
)


def parse_col_types(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the column types of a dataframe.

    Args:
        df: A pandas DataFrame.

    Returns:
        A DataFrame with the column types.
    """
    for col in df.columns:
        # SteamIDs should be ints
        if "steamid" in col:
            df[col] = df[col].astype(str)
    return df


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


def parse_rounds(parser: DemoParser) -> pd.DataFrame:
    """Parse the rounds of the demofile.

    Args:
        parser: The parser object.

    Returns:
        The rounds for the demofile.

    Raises:
        KeyError: If a round-related event is not found in the events.
    """
    round_start = parser.parse_event("round_start")
    if len(round_start) == 0:
        round_start_missing_msg = "round_start not found in events."
        raise KeyError(round_start_missing_msg)
    round_start["event"] = "start"

    round_end = parser.parse_event("round_end")
    if len(round_end) == 0:
        round_end_missing_msg = "round_end not found in events."
        raise KeyError(round_end_missing_msg)
    round_end = round_end[~round_end["winner"].isna()]  # Remove None round ends
    round_end["event"] = "end"

    round_end_official = parser.parse_event("round_officially_ended")
    if len(round_end_official) == 0:
        round_end_official_missing_msg = "round_officially_ended not found in events."
        raise KeyError(round_end_official_missing_msg)
    round_end_official["event"] = "official_end"

    round_freeze_end = parser.parse_event("round_freeze_end")
    if len(round_freeze_end) == 0:
        round_freeze_end_missing_msg = "round_freeze_end not found in events."
        raise KeyError(round_freeze_end_missing_msg)
    round_freeze_end["event"] = "freeze_end"

    rounds = pd.concat(
        [
            round_start[["event", "tick"]],
            round_freeze_end[["event", "tick"]],
            round_end[["event", "tick"]],
            round_end_official[["event", "tick"]],
        ]
    )

    # Remove everything that happen on tick 0, except starts
    rounds = rounds[~((rounds["tick"] == 0) & (rounds["event"] != "start"))]

    # Then, order
    event_order = ["official_end", "start", "freeze_end", "end"]
    rounds["event"] = pd.Categorical(
        rounds["event"], categories=event_order, ordered=True
    )
    rounds = (
        rounds.sort_values(by=["tick", "event"])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Initialize an empty list to store the indices of rows to keep
    indices_to_keep = []

    # Loop through the DataFrame and check for the correct order of events
    full_sequence_offset = len(event_order)
    for i in range(len(rounds)):
        # Extract the current sequence of events
        current_sequence = rounds["event"].iloc[i : i + full_sequence_offset].tolist()
        # Check if the current sequence matches the correct order
        if current_sequence == ["start", "freeze_end", "end", "official_end"]:
            # If it does, add the indices of these rows to the list
            indices_to_keep.extend(range(i, i + full_sequence_offset))
        # Case for end of match where we might not get a round official end
        # Case for start of match where we might not get a freeze end
        elif current_sequence == ["start", "freeze_end", "end"] or current_sequence[
            0 : full_sequence_offset - 1
        ] == [
            "start",
            "end",
            "official_end",
        ]:
            indices_to_keep.extend(range(i, i + full_sequence_offset - 1))

    # Filter the DataFrame to keep only the rows with the correct sequence
    rounds_filtered = rounds.loc[indices_to_keep].reset_index(drop=True)
    rounds_filtered["round"] = (rounds_filtered["event"] == "start").cumsum()
    rounds_reshaped = rounds_filtered.pivot_table(
        index="round", columns="event", values="tick", aggfunc="first", observed=False
    ).reset_index(drop=True)
    rounds_reshaped = rounds_reshaped[
        ["start", "freeze_end", "end", "official_end"]
    ].astype("Int32")
    rounds_reshaped.columns = ["start", "freeze_end", "end", "official_end"]
    rounds_reshaped = rounds_reshaped.merge(
        round_end[
            [
                "tick",
                "winner",
                "reason",
            ]
        ],
        left_on="end",
        right_on="tick",
        how="left",
    )
    rounds_reshaped["round"] = rounds_reshaped.index + 1
    rounds_reshaped["official_end"] = rounds_reshaped["official_end"].fillna(
        rounds_reshaped["end"]
    )
    return rounds_reshaped[
        ["round", "start", "freeze_end", "end", "official_end", "winner", "reason"]
    ]


def parse_kills(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the kills of the demofile.

    Args:
        events: A dictionary of parsed events.

    Returns:
        The kills for the demofile.

    Raises:
        KeyError: If the player_death event is not found in the events.
    """
    # Get the kill events
    kill_df = events.get("player_death")
    if kill_df is None:
        player_death_missing_msg = "player_death not found in events."
        raise KeyError(player_death_missing_msg)

    # Filter out nonplay ticks
    kill_df = parse_col_types(remove_nonplay_ticks(kill_df))

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
            "weapon",
            # Assister
            "assister_X",
            "assister_Y",
            "assister_Z",
            "assister_pitch",
            "assister_yaw",
            "assister_last_place_name",
            "assister_flash_duration",
            "assister_health",
            "assister_armor_value",
            "assister_current_equip_value",
            "assister_has_defuser",
            "assister_has_helmet",
            "assister_inventory",
            "assister_ping",
            "assister_team_name",
            "assister_team_clan_name",
            "assister_name",
            "assister_steamid",
            # Attacker
            "attacker_X",
            "attacker_Y",
            "attacker_Z",
            "attacker_pitch",
            "attacker_yaw",
            "attacker_last_place_name",
            "attacker_flash_duration",
            "attacker_health",
            "attacker_armor_value",
            "attacker_current_equip_value",
            "attacker_has_defuser",
            "attacker_has_helmet",
            "attacker_inventory",
            "attacker_ping",
            "attacker_team_name",
            "attacker_team_clan_name",
            "attacker_name",
            "attacker_steamid",
            # Victim
            "user_X",
            "user_Y",
            "user_Z",
            "user_pitch",
            "user_yaw",
            "user_last_place_name",
            "user_flash_duration",
            "user_health",
            "user_armor_value",
            "user_current_equip_value",
            "user_has_defuser",
            "user_has_helmet",
            "user_inventory",
            "user_ping",
            "user_team_name",
            "user_team_clan_name",
            "user_name",
            "user_steamid",
        ]
    ]

    # Rename columns
    for col in kill_df.columns:
        if "user_" in col:
            kill_df = kill_df.rename(columns={col: col.replace("user_", "victim_")})

    # Convert hitgroup to string
    kill_df["hitgroup"] = map_hitgroup(kill_df["hitgroup"])

    return kill_df


def parse_damages(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the damages of the demofile.

    Args:
        events: A dictionary of parsed events.

    Returns:
        The damages for the demofile.

    Raises:
        KeyError: If the player_death event is not found in the events.
    """
    # Get the damage events
    damage_df = events.get("player_hurt")
    if damage_df is None:
        player_hurt_missing_msg = "player_hurt not found in events."
        raise KeyError(player_hurt_missing_msg)

    # Filter out nonplay ticks
    damage_df = parse_col_types(remove_nonplay_ticks(damage_df))

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
            "attacker_armor_value",
            "attacker_current_equip_value",
            "attacker_has_defuser",
            "attacker_has_helmet",
            "attacker_inventory",
            "attacker_ping",
            "attacker_team_name",
            "attacker_team_clan_name",
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
            "user_armor_value",
            "user_current_equip_value",
            "user_has_defuser",
            "user_has_helmet",
            "user_inventory",
            "user_ping",
            "user_team_name",
            "user_team_clan_name",
            "user_name",
        ]
    ]

    # Rename columns
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


def parse_bomb(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the bomb events of the demofile.

    Args:
        events: A dictionary of parsed events.

    Returns:
        The bomb events for the demofile.
    """
    bomb_subevents = []

    # Get bomb plants
    bomb_planted = events.get("bomb_planted")
    if bomb_planted is None:
        logger.warning("bomb_planted not found in events.")
    else:
        bomb_planted["event"] = "planted"
        bomb_planted = parse_col_types(
            remove_nonplay_ticks(
                bomb_planted[
                    [
                        "is_freeze_period",
                        "is_warmup_period",
                        "is_terrorist_timeout",
                        "is_ct_timeout",
                        "is_technical_timeout",
                        "is_waiting_for_resume",
                        "is_match_started",
                        "game_phase",
                        "tick",
                        "event",
                        "user_last_place_name",
                        "user_X",
                        "user_Y",
                        "user_Z",
                    ]
                ]
            )
        )
        bomb_subevents.append(bomb_planted)

    # Get bomb defuses
    bomb_defused = events.get("bomb_defused")
    if bomb_defused is None:
        logger.warning("bomb_defused not found in events.")
    else:
        bomb_defused["event"] = "defused"
        bomb_defused = parse_col_types(
            remove_nonplay_ticks(
                bomb_defused[
                    [
                        "is_freeze_period",
                        "is_warmup_period",
                        "is_terrorist_timeout",
                        "is_ct_timeout",
                        "is_technical_timeout",
                        "is_waiting_for_resume",
                        "is_match_started",
                        "game_phase",
                        "tick",
                        "event",
                        "user_last_place_name",
                        "user_X",
                        "user_Y",
                        "user_Z",
                    ]
                ]
            )
        )
        bomb_subevents.append(bomb_defused)

    # Get bomb explosions
    bomb_exploded = events.get("bomb_exploded")
    if bomb_exploded is None:
        logger.warning("bomb_exploded not found in events.")
    else:
        bomb_exploded["event"] = "exploded"
        bomb_exploded = parse_col_types(
            remove_nonplay_ticks(
                bomb_exploded[
                    [
                        "is_freeze_period",
                        "is_warmup_period",
                        "is_terrorist_timeout",
                        "is_ct_timeout",
                        "is_technical_timeout",
                        "is_waiting_for_resume",
                        "is_match_started",
                        "game_phase",
                        "tick",
                        "event",
                        "user_last_place_name",
                        "user_X",
                        "user_Y",
                        "user_Z",
                    ]
                ]
            )
        )
        bomb_subevents.append(bomb_exploded)

    # Have to return an empty dataframe
    if len(bomb_subevents) == 0:
        return pd.DataFrame(columns=["tick", "event", "site", "X", "Y", "Z"])

    # Combine all bomb events
    bomb_df = pd.concat(bomb_subevents)

    # Rename columns
    bomb_df = bomb_df.rename(columns={"user_last_place_name": "site"})
    for col in bomb_df.columns:
        if "user_" in col:
            bomb_df = bomb_df.rename(columns={col: col.replace("user_", "")})

    # Handle bomb locations
    bomb_df = bomb_df.sort_values("tick").reset_index(drop=True)
    for i, row in bomb_df.iterrows():
        if row["event"] == "exploded" and i > 0:
            # The prior row will contain the correct site.
            bomb_df.loc[i, "site"] = bomb_df.loc[i - 1, "site"]
            bomb_df.loc[i, "X"] = bomb_df.loc[i - 1, "X"]
            bomb_df.loc[i, "Y"] = bomb_df.loc[i - 1, "Y"]
            bomb_df.loc[i, "Z"] = bomb_df.loc[i - 1, "Z"]
    return bomb_df


def parse_smokes(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the smokes of the demofile.

    Args:
        events: A dictionary of parsed events.

    Returns:
        The smokes for the demofile.

    Raises:
        KeyError: If smokegrenade_detonate or smokegrenade_expired is not
            found in the events.
    """
    # Get smoke starts
    smoke_starts = events.get("smokegrenade_detonate")
    if smoke_starts is None:
        smokegrenade_detonate_missing_msg = "smokegrenade_detonate not found in events."
        raise KeyError(smokegrenade_detonate_missing_msg)

    smoke_starts = parse_col_types(remove_nonplay_ticks(smoke_starts))

    # Get smoke ends
    smoke_ends = events.get("smokegrenade_expired")
    if smoke_ends is None:
        smokegrenade_expired_missing_msg = "smokegrenade_expired not found in events."
        raise KeyError(smokegrenade_expired_missing_msg)

    smoke_ends = parse_col_types(remove_nonplay_ticks(smoke_ends))

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
            "thrower_team_clan_name": start_row["user_team_clan_name"],
            "thrower_team_name": start_row["user_team_name"],
            "thrower_steamid": start_row["user_steamid"],
            "X": start_row["x"],
            "Y": start_row["y"],
            "Z": start_row["z"],
        }
        matched_rows.append(combined_row)
    return pd.DataFrame(matched_rows)


def parse_infernos(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the infernos of the demofile.

    Args:
        events: A dictionary of parsed events.

    Returns:
        The infernos for the demofile.

    Raises:
        KeyError: If inferno_startburn or inferno_expire is not found in the events.
    """
    # Get inferno starts
    inferno_starts = events.get("inferno_startburn")
    if inferno_starts is None:
        inferno_startburn_missing_msg = "inferno_startburn not found in events."
        raise KeyError(inferno_startburn_missing_msg)

    inferno_starts = parse_col_types(remove_nonplay_ticks(inferno_starts))

    # Get inferno ends
    inferno_ends = events.get("inferno_expire")
    if inferno_ends is None:
        inferno_expire_missing_msg = "inferno_expire not found in events."
        raise KeyError(inferno_expire_missing_msg)

    inferno_ends = parse_col_types(remove_nonplay_ticks(inferno_ends))
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
            "thrower_team_clan_name": start_row["user_team_clan_name"],
            "thrower_team_name": start_row["user_team_name"],
            "thrower_steamid": start_row["user_steamid"],
            "X": start_row["x"],
            "Y": start_row["y"],
            "Z": start_row["z"],
        }
        matched_rows.append(combined_row)
    return pd.DataFrame(matched_rows)


def parse_weapon_fires(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse the weapon fires of the demofile.

    Args:
        events: A dictionary of parsed events.

    Returns:
        The weapon fires for the demofile.

    Raises:
        KeyError: If the weapon_fire event is not found in the events.
    """
    weapon_fires_df = events.get("weapon_fire")
    if weapon_fires_df is None:
        weapon_fire_missing_msg = "weapon_fire not found in events."
        raise KeyError(weapon_fire_missing_msg)

    weapon_fires_df = parse_col_types(remove_nonplay_ticks(weapon_fires_df))
    weapon_fires_df = weapon_fires_df[
        [
            "tick",
            "user_name",
            "user_steamid",
            "user_team_name",
            "user_team_clan_name",
            "user_X",
            "user_Y",
            "user_Z",
            "user_yaw",
            "user_pitch",
            "user_last_place_name",
            # "user_is_strafing", #deactivated for now
            "user_accuracy_penalty",
            "user_health",
            "user_armor_value",
            "user_zoom_lvl",
            "user_inventory",
            "weapon",
        ]
    ]

    # Rename columns
    for col in weapon_fires_df.columns:
        if "user_" in col:
            weapon_fires_df = weapon_fires_df.rename(
                columns={col: col.replace("user_", "player_")}
            )
    return weapon_fires_df


def parse_ticks(
    parser: DemoParser, player_props: list[str], other_props: list[str]
) -> pd.DataFrame:
    """Parse the ticks of the demofile.

    Args:
        parser (DemoParser): The parser object.
        player_props (list[str]): Player properties to parse.
        other_props (list[str]): World properties to parse.

    Returns:
        pd.DataFrame: The ticks for the demofile.
    """
    ticks = parser.parse_ticks(wanted_props=player_props + other_props)
    return parse_col_types(remove_nonplay_ticks(ticks))
