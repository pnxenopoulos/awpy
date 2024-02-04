"""Parsing methods for damage and kill-related events."""

import warnings

import pandas as pd


def parse_damages(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the damages of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with damage events.

    Returns:
        pd.DataFrame: DataFrame with the parsed damage events data.
    """
    if not parsed:
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

    # Assuming the first element of 'parsed' always contains the relevant DataFrame
    damage_df = parsed[0][1]

    # Renaming columns
    rename_columns = {
        "attacker_name": "attacker",
        "user_name": "victim",
        "user_steamid": "victim_steamid",
    }
    damage_df = damage_df.rename(columns=rename_columns)

    # Converting data types
    for col in ["attacker_steamid", "victim_steamid"]:
        damage_df[col] = damage_df[col].astype("Int64")

    return damage_df.sort_values(by="tick")


def parse_deaths(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the deaths of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with death events.

    Returns:
        pd.DataFrame: DataFrame with the parsed death events data.
    """
    if not parsed:
        warnings.warn("No deaths found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=[
                "assistedflash",
                "assister",
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

    # Assuming the first element of 'parsed' always contains the relevant DataFrame
    death_df = parsed[0][1]

    # Renaming columns
    rename_columns = {
        "assister_name": "assister",
        "attacker_name": "attacker",
        "user_name": "victim",
        "user_steamid": "victim_steamid",
    }
    death_df = death_df.rename(columns=rename_columns)

    # Converting data types
    for col in ["attacker_steamid", "assister_steamid", "victim_steamid"]:
        death_df[col] = death_df[col].astype("Int64")

    return death_df.sort_values(by="tick")


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

    for i in range(kill_index):
        previous_kill = df.iloc[i]

        # If the previous kill was too long ago, stop looping
        if not kill_tick - trade_time <= previous_kill["tick"] < kill_tick:
            break

        # If the previous kill did not have a valid side, skip it
        if pd.isna(previous_kill["attacker_side"]) or pd.isna(
            previous_kill["victim_side"]
        ):
            continue

        if (
            previous_kill["attacker_steamid"] == kill_victim
            and previous_kill["attacker_side"] != previous_kill["victim_side"]
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
    if kill_index >= len(df) - 1:
        return False

    current_kill = df.iloc[kill_index]
    kill_attacker = current_kill["attacker_steamid"]
    kill_tick = current_kill["tick"]

    for i in range(kill_index + 1, len(df)):
        next_kill = df.iloc[i]
        if (
            kill_tick <= next_kill["tick"] < kill_tick + trade_time
            and next_kill["victim_steamid"] == kill_attacker
            and next_kill["attacker_side"] != next_kill["victim_side"]
        ):
            return True

    return False


def add_trade_info(df: pd.DataFrame, trade_time: int) -> pd.DataFrame:
    """Add trade kill and was traded columns to a DataFrame of kills.

    Args:
        df (pd.DataFrame): DataFrame of kills.
        trade_time (int): Ticks between kills.

    Returns:
        pd.DataFrame: DataFrame of kills with trade kill and was traded columns.
    """
    df["is_trade"] = df.apply(
        lambda row: is_trade_kill(df, row.name, trade_time), axis=1
    )
    df["was_traded"] = df.apply(
        lambda row: was_traded(df, row.name, trade_time), axis=1
    )
    return df
