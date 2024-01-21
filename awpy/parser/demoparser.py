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

from awpy.parser import enums, models


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


def parse_header(parsed_header: dict) -> models.DemoHeader:
    """Parse the header of the demofile.

    Args:
        parsed_header (dict): The header of the demofile.

    Returns:
        models.DemoHeader: The parsed header of the demofile.
    """
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
    return models.DemoHeader(**parsed_header)


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
        if round_event[0] == enums.GameEvent.ROUND_END.value:
            round_events.append(round_event[1].loc[:, ["tick", "event", "reason"]])
        else:
            round_events.append(round_event[1].loc[:, ["tick", "event"]])
    round_event_df = pd.concat(round_events)

    # Ascribe order to event types and sort by tick and order
    event_order = {
        enums.GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
        enums.GameEvent.ROUND_START.value: 1,
        enums.GameEvent.ROUND_FREEZE_END.value: 2,
        enums.GameEvent.BUYTIME_ENDED.value: 3,
        enums.GameEvent.ROUND_END.value: 4,
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
        case enums.GameEvent.ROUND_START.value:
            pass
        case _:
            round_event_df = pd.concat(
                [
                    pd.DataFrame(
                        {
                            "tick": [0],
                            "event": [enums.GameEvent.ROUND_START.value],
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
    final_df = final_df[~final_df["round_end_reason"].isna()]

    final_df["round_num"] = range(1, len(final_df) + 1)
    final_df["round_end_official"] = final_df["round_end_official"].fillna(
        final_df["round_end"]
    )

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
    return smoke_inferno_df.sort_values(by=["tick", "entityid"])


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
            case enums.GameEvent.BOMB_PLANTED.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
            case enums.GameEvent.BOMB_DEFUSED.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
            case enums.GameEvent.BOMB_BEGINDEFUSE.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "haskit"]]
            case enums.GameEvent.BOMB_BEGINPLANT.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
            case enums.GameEvent.BOMB_EXPLODED.value:
                parsed_df = parsed_df[["tick", "event", "player", "steamid", "site"]]
        all_event_dfs.append(parsed_df)

    bomb_df = pd.concat(all_event_dfs)
    bomb_df["steamid"] = bomb_df["steamid"].astype("Int64")

    return bomb_df.sort_values(by=["tick"])


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

    return damage_df.sort_values(by=["tick"])


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

    return blind_df.sort_values(by=["tick"])


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

    return weapon_fires_df.sort_values(by=["tick"])


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
        [tick_df["team_num"] == enums.Side.T.value, tick_df["team_num"] == enums.Side.CT.value],
        ["t", "ct"],
        default="spectator",
    )
    tick_df["game_phase"] = tick_df["game_phase"].replace(
        {
            0: "init",
            1: "pregame",
            2: "startgame",
            3: "preround",
            4: "teamwin",
            5: "restart",
            6: "stalemate",
            7: "gameover",
        }
    )
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
                "spotted",
            ]
        )
    )
    tick_df = tick_df[intersection]

    tick_df["steamid"] = tick_df["steamid"].astype("Int64")

    return tick_df


def is_trade_kill(df: pd.DataFrame, kill_index: int, trade_time: int) -> bool:
    """Check if a kill is a trade kill.

    Args:
        df (pd.DataFrame): DataFrame of kills.
        kill_index (int): Row to check for trade kill status.
        trade_time (int): Ticks between kills.

    Returns:
        bool: True if the kill_index row of `df` is a trade kill. False otherwise.
    """
    if kill_index == 0:
        return False
    current_kill = df.iloc[kill_index]
    kill_victim = current_kill["victim_steamid"]
    kill_tick = current_kill["tick"]
    # Define the tick range for a trade kill
    trade_tick_range = range(max(kill_tick - trade_time, 0), kill_tick)
    # Check subsequent kills for a trade kill
    for i in range(max(0, kill_index - 1) + 1):
        subsequent_kill = df.iloc[i]
        if (
            subsequent_kill["tick"] in trade_tick_range
            and subsequent_kill["attacker_steamid"] == kill_victim
            and subsequent_kill["attacker_side"] != subsequent_kill["victim_side"]
        ):
            return True
    return False


def was_traded(df: pd.DataFrame, kill_index: int, trade_time: int) -> bool:
    """Check if a kill was traded later.

    Args:
        df (pd.DataFrame): DataFrame of kills.
        kill_index (int): Row to check for trade kill status.
        trade_time (int): Ticks between kills.

    Returns:
        bool: True if the kill_index row of `df` was traded later. False otherwise.
    """
    current_kill = df.iloc[kill_index]
    kill_attacker = current_kill["attacker_steamid"]
    kill_tick = current_kill["tick"]
    # Define the tick range for a trade kill
    trade_tick_range = range(kill_tick, kill_tick + trade_time)
    # Check subsequent kills for a trade kill
    for i in range(kill_index, df.shape[0] + 1):
        if i == df.shape[0]:
            break
        next_kill = df.iloc[i]
        if (
            next_kill["tick"] in trade_tick_range
            and next_kill["victim_steamid"] == kill_attacker
            and next_kill["attacker_side"] != next_kill["victim_side"]
        ):
            return True
    return False


def parse_demo(file: str, trade_time: int = 640) -> models.Demo:
    """Parse the demofile.

    Args:
        file (str): Path to the demofile.
        trade_time (int, optional): Ticks between kills. Defaults to 640.

    Returns:
        models.Demo: Dictionary with the parsed data. Has keys `header`, `rounds`, `kills`,
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
            enums.GameEvent.ROUND_START.value,
            enums.GameEvent.ROUND_FREEZE_END.value,
            enums.GameEvent.BUYTIME_ENDED.value,
            enums.GameEvent.ROUND_END.value,
            enums.GameEvent.ROUND_OFFICIALLY_ENDED.value,
        ]
    )
    round_df = parse_rounds(parsed_round_events)

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
                enums.GameState.GAME_PHASE.value,
                # Location
                enums.PlayerData.X.value,
                enums.PlayerData.Y.value,
                enums.PlayerData.Z.value,
                enums.PlayerData.PITCH.value,
                enums.PlayerData.YAW.value,
                enums.PlayerData.LAST_PLACE_NAME.value,
                # Health/Armor/Weapon
                enums.PlayerData.IS_ALIVE.value,
                enums.PlayerData.HEALTH.value,
                enums.PlayerData.ARMOR.value,
                enums.PlayerData.HAS_HELMET.value,
                enums.PlayerData.HAS_DEFUSER.value,
                enums.PlayerData.ACTIVE_WEAPON.value,
                enums.PlayerData.CURRENT_EQUIP_VALUE.value,
                enums.PlayerData.ROUND_START_EQUIP_VALUE.value,
                # Rank
                enums.PlayerData.RANK.value,
                # Extra
                enums.PlayerData.PING.value,
                enums.PlayerData.CLAN_NAME.value,
                enums.PlayerData.TEAM_NUM.value,
                enums.PlayerData.FLASH_DURATION.value,
                enums.PlayerData.FLASH_MAX_ALPHA.value,
                enums.PlayerData.IS_SCOPED.value,
                enums.PlayerData.IS_DEFUSING.value,
                enums.PlayerData.IS_WALKING.value,
                enums.PlayerData.IS_STRAFING.value,
                enums.PlayerData.IN_BUY_ZONE.value,
                enums.PlayerData.IN_BOMB_ZONE.value,
                enums.PlayerData.SPOTTED.value,
            ],
        )
        tick_df = parse_frame(tick_df)
        tick_df = apply_round_num_to_df(tick_df, round_df)
    except Exception as err:
        warn_msg = f"Error parsing tick data found in the demofile: {err}"
        warnings.warn(warn_msg, stacklevel=2)

    # Damages
    damage = parser.parse_events([enums.GameEvent.PLAYER_HURT.value], other=["game_phase"])
    damage_df = parse_damages(damage)
    damage_df = apply_round_num_to_df(damage_df, round_df)

    # Add sides to damage_df
    damage_df = damage_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "attacker_steamid"],
        right_on=["tick", "steamid"],
    )
    damage_df = damage_df.rename(columns={"side": "attacker_side"})
    damage_df = damage_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "victim_steamid"],
        right_on=["tick", "steamid"],
    )
    damage_df = damage_df.rename(columns={"side": "victim_side"})

    # Blockers (smokes, molotovs, etc.)
    effect = parser.parse_events(
        [
            enums.GameEvent.INFERNO_STARTBURN.value,
            enums.GameEvent.INFERNO_EXPIRE.value,
            enums.GameEvent.SMOKEGRENADE_DETONATE.value,
            enums.GameEvent.SMOKEGRENADE_EXPIRED.value,
        ]
    )
    effect_df = parse_smokes_and_infernos(effect)
    effect_df = apply_round_num_to_df(effect_df, round_df)

    # Bomb
    bomb = parser.parse_events(
        [
            enums.GameEvent.BOMB_BEGINDEFUSE.value,
            enums.GameEvent.BOMB_BEGINPLANT.value,
            enums.GameEvent.BOMB_DEFUSED.value,
            enums.GameEvent.BOMB_EXPLODED.value,
            enums.GameEvent.BOMB_PLANTED.value,
        ]
    )
    bomb_df = parse_bomb_events(bomb)
    bomb_df = apply_round_num_to_df(bomb_df, round_df)

    # Deaths
    deaths = parser.parse_events(
        [
            enums.GameEvent.PLAYER_DEATH.value,
        ],
    )
    death_df = parse_deaths(deaths)
    death_df = apply_round_num_to_df(death_df, round_df)

    # Add sides to death_df
    death_df = death_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "attacker_steamid"],
        right_on=["tick", "steamid"],
    )
    death_df = death_df.drop("steamid", axis=1)
    death_df = death_df.rename(columns={"side": "attacker_side"})

    death_df = death_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "victim_steamid"],
        right_on=["tick", "steamid"],
    )
    death_df = death_df.drop("steamid", axis=1)
    death_df = death_df.rename(columns={"side": "victim_side"})

    death_df = death_df.merge(
        tick_df[["tick", "steamid", "side"]],
        left_on=["tick", "assister_steamid"],
        right_on=["tick", "steamid"],
        how="left",
    )
    death_df = death_df.drop("steamid", axis=1)
    death_df = death_df.rename(columns={"side": "assister_side"})

    death_df["is_trade"] = death_df.apply(
        lambda row: is_trade_kill(death_df, row.name, trade_time), axis=1
    )
    death_df["was_traded"] = death_df.apply(
        lambda row: was_traded(death_df, row.name, trade_time), axis=1
    )

    # Blinds
    blinds = parser.parse_events([enums.GameEvent.PLAYER_BLIND.value])
    blinds_df = parse_blinds(blinds)
    blinds_df = apply_round_num_to_df(blinds_df, round_df)

    # Weapon Fires
    weapon_fires = parser.parse_events([enums.GameEvent.WEAPON_FIRE.value])
    weapon_fires_df = parse_weapon_fires(weapon_fires)
    weapon_fires_df = apply_round_num_to_df(weapon_fires_df, round_df)

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
        grenade_df = apply_round_num_to_df(grenade_df, round_df)
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

    return models.Demo(**parsed_data)
