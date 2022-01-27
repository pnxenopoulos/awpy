import operator
from typing import Dict, List, Tuple, Union

import pandas as pd


def extract_num_filters(
    filters: Dict[str, Union[List[bool], List[str]]], key: str
) -> Tuple[List[str], List[float]]:
    """Extracts the numeric column filters from a key-value pair in a
       dictionary.

    Extracts logical operators and numeric values from the column filters in the
    the value of a specified key in the dictionary represented by filters.

    Args:
        filters: A dictionary where the keys are the columns of the dataframe
            represented by df to filter the data by and the values are lists
            that contain the column filters.
        key: The key in the dictionary represented by filters for which the
            numeric column filters should be extracted.

    Returns:
        A tuple of two lists where the first list contains all of the logical
        operators in the column filters in the value of a specified key and the
        second list contains all of the numeric values in the column filters in
        the value of a specified key. For example:
        ([">", "<"], [15.0, 25.0])

    Raises:
        ValueError: The value of the specified key contains a column filter of
            type boolean.
        Exception: The column filters in the value of the specified key contain
            an invalid logical operator.
        Exception: The column filters in the value of the specified key contain
            an invalid numeric value.
    """
    sign_list = []
    val_list = []
    for index in filters[key]:
        if not isinstance(index, str):
            raise ValueError(
                f'Filter(s) for column "{key}" must be of type ' f"string."
            )
        i = 0
        sign = ""
        while i < len(index) and not index[i].isdecimal():
            sign += index[i]
            end_index = i
            i += 1
        if sign not in ("==", "!=", "<=", ">=", "<", ">"):
            raise Exception(
                f'Invalid logical operator in filters for "{key}"' f" column."
            )
        sign_list.append(sign)
        try:
            val_list.append(float(index[end_index + 1 :]))
        except ValueError as ve:
            raise Exception(
                f'Invalid numerical value in filters for "{key}" ' f"column."
            ) from ve
    return sign_list, val_list


def check_filters(df: pd.DataFrame, filters: Dict[str, Union[List[bool], List[str]]]):
    """Checks if the column filters are valid.

    Iterates through each key-value pair in the dictionary represented by
    filters and checks if the column filters for columns of type boolean are
    of type boolean and the column filters for columns of type string are of
    type string. Calls the function extract_numeric_filters to check if the
    column filters for columns of type float and integer are valid.

    Args:
        df: A dataframe to be filtered.
        filters: A dictionary where the keys are the columns of the dataframe
            represented by df to filter the data by and the values are lists
            that contain the column filters.

    Raises:
        ValueError: The value of a key corresponding to a column of type boolean
            contains a column filter of a different type.
        ValueError: The value of a key corresponding to a column of type string
            contains a column filter of a different type.
    """
    for key in filters:
        if df.dtypes[key] == "bool":
            for index in filters[key]:
                if not isinstance(index, bool):
                    raise ValueError(
                        f'Filter(s) for column "{key}" must be ' f"of type boolean"
                    )
        elif df.dtypes[key] == "O":
            for index in filters[key]:
                if not isinstance(index, str):
                    raise ValueError(
                        f'Filter(s) for column "{key}" must be ' f"of type string"
                    )
        else:
            extract_num_filters(filters, key)


def num_filter_df(df: pd.DataFrame, col: str, sign: str, val: float) -> pd.DataFrame:
    """Filters numeric data in a dataframe.

    Args:
        df: A dataframe to be filtered.
        col: A column of the dataframe represented by df to filter by.
        sign: A logical operator representing the operation to filter the
            dataframe represented by df by.
        val: A numeric value to filter the dataframe represented by df by.

    Returns:
        A filtered dataframe.
    """
    ops = {
        "==": operator.eq(df[col], val),
        "!=": operator.ne(df[col], val),
        "<=": operator.le(df[col], val),
        ">=": operator.ge(df[col], val),
        "<": operator.lt(df[col], val),
        ">": operator.gt(df[col], val),
    }
    filtered_df = df.loc[ops[sign]]
    return filtered_df


def filter_df(
    df: pd.DataFrame, filters: Dict[str, Union[List[bool], List[str]]]
) -> pd.DataFrame:
    """Filters data in a dataframe.

    Filters a dataframe for columns of type boolean and string and calls the
    function num_filter_df to filter a dataframe for columns of type float
    and integer.

    Args:
        df: A dataframe to be filtered.
        filters: A dictionary where the keys are the columns of the dataframe
            represented by df to filter the data by and the values are lists
            that contain the column filters.

    Returns:
        A filtered dataframe.
    """
    df_copy = df.copy()
    check_filters(df_copy, filters)
    for key in filters:
        if df_copy.dtypes[key] == "bool" or df_copy.dtypes[key] == "O":
            df_copy = df_copy.loc[df_copy[key].isin(filters[key])]
        else:
            i = 0
            for _ in extract_num_filters(filters, key)[0]:
                val = extract_num_filters(filters, key)[1][i]
                df_copy = num_filter_df(
                    df_copy, key, extract_num_filters(filters, key)[0][i], val
                )
                i += 1
    return df_copy


def calc_stats(
    df: pd.DataFrame,
    filters: Dict[str, Union[List[bool], List[str]]],
    col_to_groupby: List[str],
    col_to_agg: List[str],
    agg: List[List[str]],
    col_names: List[str],
) -> pd.DataFrame:
    """Calculates statistics for a dataframe.

    Calls the function filter_df to filter a data in dataframe and then performs
    groupby and aggregation operations on the dataframe and renames the columns.

    Args:
        df: A dataframe from which statistics should be calculated.
        filters: A dictionary where the keys are the columns of the dataframe
            represented by df to filter the data by and the values are lists
            that contain the column filters.
        col_to_groupby: Columns of the dataframe represented by df to perform
            the groupby operation on.
        col_to_agg: Columns of the dataframe represented by df to perform
            aggregation operations on.
        agg: The aggregation operations to be applied to the columns in the list
            represented by col_to_agg.
        col_names: Column names for the returned dataframe.

    Returns:
        A dataframe with the specified statistics.
    """
    df_copy = filter_df(df, filters)
    agg_dict = dict(zip(col_to_agg, agg))
    if col_to_agg:
        df_copy = df_copy.groupby(col_to_groupby).agg(agg_dict).reset_index()
    df_copy.columns = col_names
    return df_copy


def accuracy(
    damage_data: pd.DataFrame,
    weapon_fire_data: pd.DataFrame,
    team: bool = False,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with accuracy statistics.

    Args:
        damage_data: A dataframe with damage data.
        weapon_fire_data: A dataframe with weapon fire data.
        team: A boolean specifying wheter to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        weapon_fire_filters: A dictionary where the keys are the columns of the
            dataframe represented by weapon_fires to filter the weapon fire data
            by and the values are lists that contain the column filters.

    Returns:
        A dataframe with the total shots, strafe shots, hits, accuracy (hits/total number of shots), headshot accuracy (head hits/total number of shots)
    """
    stats = ["playerName", "attackerName", "Player"]
    if team:
        stats = ["playerTeam", "attackerTeam", "Team"]
    weapon_fires = calc_stats(
        weapon_fire_data,
        weapon_fire_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[2], "Weapon Fires"],
    )
    strafe_fires = calc_stats(
        weapon_fire_data.loc[weapon_fire_data["playerStrafe"] == True],
        weapon_fire_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[2], "Strafe Fires"],
    )
    hits = calc_stats(
        damage_data.loc[damage_data["attackerTeam"] != damage_data["victimTeam"]],
        damage_filters,
        [stats[1]],
        [stats[1]],
        [["size"]],
        [stats[2], "Hits"],
    )
    headshots = calc_stats(
        damage_data.loc[
            (damage_data["attackerTeam"] != damage_data["victimTeam"])
            & (damage_data["hitGroup"] == "Head")
        ],
        damage_filters,
        [stats[1]],
        [stats[1]],
        [["size"]],
        [stats[2], "Headshots"],
    )
    acc = weapon_fires.merge(strafe_fires, how="outer").fillna(0)
    acc = acc.merge(hits, how="outer").fillna(0)
    acc = acc.merge(headshots, how="outer").fillna(0)
    acc["Strafe%"] = acc["Strafe Fires"] / acc["Weapon Fires"]
    acc["ACC%"] = acc["Hits"] / acc["Weapon Fires"]
    acc["HS ACC%"] = acc["Headshots"] / acc["Weapon Fires"]
    acc = acc[[stats[2], "Weapon Fires", "Strafe%", "ACC%", "HS ACC%"]]
    acc.sort_values(by="ACC%", ascending=False, inplace=True)
    acc.reset_index(drop=True, inplace=True)
    return acc


def kast(
    kill_data: pd.DataFrame,
    kast_string: str = "KAST",
    flash_assists: bool = True,
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
    death_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with KAST statistics.

    Args:
        kill_data: A dataframe with kill data.
        kast_string: A string specifying which combination of KAST statistics
            to use.
        flash_assists: A boolean specifying if flash assists are to be
            counted as assists or not.
        kill_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe containing the percentage of a player's rounds with at least one of (K)ill, (A)ssist, (S)urvival and (T)rades.
    """
    columns = ["Player", f"{kast_string.upper()}%"]
    kast_counts = {}
    kast_rounds = {}
    for stat in kast_string.upper():
        columns.append(stat)
    kill_data = kill_data[~kill_data["attackerName"].isna()]
    killers = calc_stats(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        ["roundNum"],
        ["attackerName"],
        [["sum"]],
        ["RoundNum", "Killers"],
    )
    victims = calc_stats(
        kill_data,
        kill_filters,
        ["roundNum"],
        ["victimName"],
        [["sum"]],
        ["RoundNum", "Victims"],
    )
    assisters = calc_stats(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]].fillna(""),
        kill_filters,
        ["roundNum"],
        ["assisterName"],
        [["sum"]],
        ["RoundNum", "Assisters"],
    )
    traded = calc_stats(
        kill_data.loc[
            (kill_data["attackerTeam"] != kill_data["victimTeam"])
            & (kill_data["isTrade"] == True)
        ].fillna(""),
        kill_filters,
        ["roundNum"],
        ["playerTradedName"],
        [["sum"]],
        ["RoundNum", "Traded"],
    )
    if flash_assists:
        flash_assisters = calc_stats(
            kill_data.loc[
                kill_data["flashThrowerTeam"] != kill_data["victimTeam"]
            ].fillna(""),
            kill_filters,
            ["roundNum"],
            ["flashThrowerName"],
            [["sum"]],
            ["RoundNum", "Flash Assisters"],
        )
        assisters = assisters.merge(flash_assisters, on="RoundNum")
        assisters["Assisters"] = assisters["Assisters"] + assisters["Flash Assisters"]
        assisters = assisters[["RoundNum", "Assisters"]]
    kast_data = killers.merge(assisters, how="outer").fillna("")
    kast_data = kast_data.merge(victims, how="outer").fillna("")
    kast_data = kast_data.merge(traded, how="outer").fillna("")
    killer_names = kill_data["attackerName"].tolist()
    cleaned_killer_names = []
    for x in killer_names:
        if x != None:
            cleaned_killer_names.append(x)
    cleaned_killer_names = pd.Series(cleaned_killer_names)
    for player in cleaned_killer_names:
        kast_counts[player] = [[0, 0, 0, 0] for i in range(len(kast_data))]
        kast_rounds[player] = [0, 0, 0, 0, 0]
    for rd in kast_data.index:
        for player in kast_counts:
            if "K" in kast_string.upper():
                kast_counts[player][rd][0] = kast_data.iloc[rd]["Killers"].count(player)
                kast_rounds[player][1] += kast_data.iloc[rd]["Killers"].count(player)
            if "A" in kast_string.upper():
                kast_counts[player][rd][1] = kast_data.iloc[rd]["Assisters"].count(
                    player
                )
                kast_rounds[player][2] += kast_data.iloc[rd]["Assisters"].count(player)
            if "S" in kast_string.upper():
                if player not in kast_data.iloc[rd]["Victims"]:
                    kast_counts[player][rd][2] = 1
                    kast_rounds[player][3] += 1
            if "T" in kast_string.upper():
                kast_counts[player][rd][3] = kast_data.iloc[rd]["Traded"].count(player)
                kast_rounds[player][4] += kast_data.iloc[rd]["Traded"].count(player)
    for player in kast_rounds:
        for rd in kast_counts[player]:
            if any(rd):
                kast_rounds[player][0] += 1
        kast_rounds[player][0] /= len(kast_data)
    kast = pd.DataFrame.from_dict(kast_rounds, orient="index").reset_index()
    kast.columns = ["Player", f"{kast_string.upper()}%", "K", "A", "S", "T"]
    kast = kast[columns]
    kast.fillna(0, inplace=True)
    kast.sort_values(by=f"{kast_string.upper()}%", ascending=False, inplace=True)
    kast.reset_index(drop=True, inplace=True)
    return kast


def kill_stats(
    damage_data: pd.DataFrame,
    kill_data: pd.DataFrame,
    round_data: pd.DataFrame,
    weapon_fire_data: pd.DataFrame,
    team: bool = False,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
    death_filters: Dict[str, Union[List[bool], List[str]]] = {},
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
    weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with kill statistics.

    Args:
        damage_data: A dataframe with damage data.
        kill_data: A dataframe with kill data.
        round_data: A dataframe with round data.
        weapon_fire_data: A dataframe with weapon fire data.
            where each round is a dictionary.
        team: A boolean specifying whether to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        kill_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.
        round_filters: A dictionary where the keys are the columns of the
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.
        weapon_fire_filters: A dictionary where the keys are the columns of the
            dataframe represented by weapon_fires to filter the weapon fire data
            by and the values are lists that contain the column filters.

    Returns:
        A dataframe with kills, deaths, assists, flash assists, first kills/deaths, headshots, headshot kills/total kills, KAST and accuracy statistics.
    """
    stats = ["attackerName", "victimName", "assisterName", "flashThrowerName", "Player"]
    if team:
        stats = [
            "attackerTeam",
            "victimTeam",
            "assisterTeam",
            "flashThrowerTeam",
            "Team",
        ]
    kills = calc_stats(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[4], "K"],
    )
    deaths = calc_stats(
        kill_data, death_filters, [stats[1]], [stats[1]], [["size"]], [stats[4], "D"],
    )
    assists = calc_stats(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[2]],
        [stats[2]],
        [["size"]],
        [stats[4], "A"],
    )
    flash_assists = calc_stats(
        kill_data.loc[kill_data["flashThrowerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[3]],
        [stats[3]],
        [["size"]],
        [stats[4], "FA"],
    )
    first_kills = calc_stats(
        kill_data.loc[
            (kill_data["attackerTeam"] != kill_data["victimTeam"])
            & (kill_data["isFirstKill"] == True)
        ],
        kill_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[4], "FK"],
    )
    first_deaths = calc_stats(
        kill_data.loc[
            (kill_data["attackerTeam"] != kill_data["victimTeam"])
            & (kill_data["isFirstKill"] == True)
        ],
        kill_filters,
        [stats[1]],
        [stats[1]],
        [["size"]],
        [stats[4], "FD"],
    )
    headshots = calc_stats(
        kill_data.loc[
            (kill_data["attackerTeam"] != kill_data["victimTeam"])
            & (kill_data["isHeadshot"] == True)
        ],
        kill_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[4], "HS"],
    )
    headshot_pct = calc_stats(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[0]],
        ["isHeadshot"],
        [["mean"]],
        [stats[4], "HS%"],
    )
    if not team:
        acc_stats = accuracy(
            damage_data, weapon_fire_data, False, damage_filters, weapon_fire_filters
        )
    else:
        acc_stats = accuracy(
            damage_data, weapon_fire_data, True, damage_filters, weapon_fire_filters
        )
    kast_stats = kast(kill_data, "KAST", kill_filters, death_filters)
    kill_stats = kills.merge(deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(assists, how="outer").fillna(0)
    kill_stats = kill_stats.merge(flash_assists, how="outer").fillna(0)
    kill_stats = kill_stats.merge(first_kills, how="outer").fillna(0)
    kill_stats = kill_stats.merge(first_deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(headshots, how="outer").fillna(0)
    kill_stats = kill_stats.merge(headshot_pct, how="outer").fillna(0)
    kill_stats = kill_stats.merge(acc_stats, how="outer").fillna(0)
    if not team:
        kill_stats = kill_stats.merge(kast_stats, how="outer").fillna(0)
    kill_stats["+/-"] = kill_stats["K"] - kill_stats["D"]
    kill_stats["KDR"] = kill_stats["K"] / kill_stats["D"]
    kill_stats["KPR"] = kill_stats["K"] / len(
        calc_stats(round_data, round_filters, [], [], [], round_data.columns)
    )
    kill_stats["FK +/-"] = kill_stats["FK"] - kill_stats["FD"]
    int_stats = ["K", "D", "A", "FA", "+/-", "FK", "FK +/-", "HS", "T"]
    if team:
        int_stats = int_stats[0:-1]
    kill_stats[int_stats] = kill_stats[int_stats].astype(int)
    kill_stats["HS%"] = kill_stats["HS%"].astype(float)
    order = [
        stats[4],
        "K",
        "D",
        "A",
        "FA",
        "+/-",
        "FK",
        "FK +/-",
        "T",
        "HS",
        "HS%",
        "ACC%",
        "HS ACC%",
        "KDR",
        "KPR",
        "KAST%",
    ]
    if team:
        order = order[0:8] + order[9:-1]
    kill_stats = kill_stats[order]
    kill_stats.sort_values(by="K", ascending=False, inplace=True)
    kill_stats.reset_index(drop=True, inplace=True)
    return kill_stats


def adr(
    damage_data: pd.DataFrame,
    round_data: pd.DataFrame,
    team: bool = False,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with ADR statistics.

    Args:
        damage_data: A dataframe with damage data.
        round_data: A dataframe with round data.
        team: A boolean specifying whether to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        round_filters: A dictionary where the keys are the columns of the
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with the average damage per round (ADR).
    """
    stats = ["attackerName", "Player"]
    if team:
        stats = ["attackerTeam", "Team"]
    adr = calc_stats(
        damage_data.loc[damage_data["attackerTeam"] != damage_data["victimTeam"]],
        damage_filters,
        [stats[0]],
        ["hpDamageTaken", "hpDamage"],
        [["sum"], ["sum"]],
        [stats[1], "Norm ADR", "Raw ADR"],
    )
    adr["Norm ADR"] = adr["Norm ADR"] / len(
        calc_stats(round_data, round_filters, [], [], [], round_data.columns)
    )
    adr["Raw ADR"] = adr["Raw ADR"] / len(
        calc_stats(round_data, round_filters, [], [], [], round_data.columns)
    )
    adr.sort_values(by="Norm ADR", ascending=False, inplace=True)
    adr.reset_index(drop=True, inplace=True)
    return adr


def rating(
    damage_data: pd.DataFrame,
    kill_data: pd.DataFrame,
    round_data: pd.DataFrame,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    death_filters: Dict[str, Union[List[bool], List[str]]] = {},
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with an HLTV-esque rating, found by doing:

    Rating = 0.0073*KAST + 0.3591*KPR + -0.5329*DPR + 0.2372*Impact + 0.0032*ADR + 0.1587
    where Impact = 2.13*KPR + 0.42*Assist per Round -0.41

    Args:
        damage_data: A dataframe with damage data.
        kill_data: A dataframe with damage data.
        round_data: A dataframe with round data.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.
        kill_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        round_filters: A dictionary where the keys are the columns of the
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with the impact rating and rating 2.0
    """
    kast_stats = kast(kill_data, "KAST", kill_filters, death_filters)
    kast_stats = kast_stats[["Player", "KAST%"]]
    kast_stats.columns = ["Player", "KAST"]
    adr_stats = adr(damage_data, round_data, damage_filters, round_filters)
    adr_stats = adr_stats[["Player", "Norm ADR"]]
    adr_stats.columns = ["Player", "ADR"]
    stats = ["attackerName", "victimName", "assisterName", "flashThrowerName", "Player"]
    kills = calc_stats(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[4], "K"],
    )
    deaths = calc_stats(
        kill_data, death_filters, [stats[1]], [stats[1]], [["size"]], [stats[4], "D"],
    )
    assists = calc_stats(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[2]],
        [stats[2]],
        [["size"]],
        [stats[4], "A"],
    )
    kill_stats = kills.merge(deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(assists, how="outer").fillna(0)
    kill_stats["KPR"] = kill_stats["K"] / len(
        calc_stats(round_data, round_filters, [], [], [], round_data.columns)
    )
    kill_stats["DPR"] = kill_stats["D"] / len(
        calc_stats(round_data, round_filters, [], [], [], round_data.columns)
    )
    kill_stats["APR"] = kill_stats["A"] / len(
        calc_stats(round_data, round_filters, [], [], [], round_data.columns)
    )
    kill_stats = kill_stats[["Player", "KPR", "DPR", "APR"]]
    kill_stats = kill_stats.merge(adr_stats, how="outer").fillna(0)
    kill_stats = kill_stats.merge(kast_stats, how="outer").fillna(0)
    kill_stats["Impact"] = 2.13 * kill_stats["KPR"] + 0.42 * kill_stats["APR"] - 0.41
    kill_stats["Rating"] = (
        0.73 * kill_stats["KAST"]
        + 0.3591 * kill_stats["KPR"]
        - 0.5329 * kill_stats["DPR"]
        + 0.2372 * kill_stats["Impact"]
        + 0.0032 * kill_stats["ADR"]
        + 0.1587
    )
    kill_stats = kill_stats[["Player", "Impact", "Rating"]]
    kill_stats.sort_values(by="Rating", ascending=False, inplace=True)
    kill_stats.reset_index(drop=True, inplace=True)
    return kill_stats


def util_dmg(
    damage_data: pd.DataFrame,
    grenade_data: pd.DataFrame,
    team: bool = False,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with utility damage statistics.

    Args:
        damage_data: A dataframe with damage data.
        grenade_data: A dataframe with grenade data.
        team: A boolean specifying whether to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the
            dataframe represented by grenade_data to filter the grenade data by
            and the values are lists that contain the column filters.

    Returns:
        A dataframe with nades thrown, given utility damage (UD) per nade
    """
    stats = ["attackerName", "throwerName", "Player"]
    if team:
        stats = ["attackerTeam", "throwerTeam", "Team"]
    util_dmg = calc_stats(
        damage_data.loc[
            (damage_data["attackerTeam"] != damage_data["victimTeam"])
            & (
                damage_data["weapon"].isin(
                    ["HE Grenade", "Incendiary Grenade", "Molotov"]
                )
            )
        ],
        damage_filters,
        [stats[0]],
        ["hpDamageTaken", "hpDamage"],
        [["sum"], ["sum"]],
        [stats[2], "Given UD", "UD"],
    )
    nades_thrown = calc_stats(
        grenade_data.loc[
            grenade_data["grenadeType"].isin(
                ["HE Grenade", "Incendiary Grenade", "Molotov"]
            )
        ],
        grenade_filters,
        [stats[1]],
        [stats[1]],
        [["size"]],
        [stats[2], "Nades Thrown"],
    )
    util_dmg_stats = util_dmg.merge(nades_thrown, how="outer").fillna(0)
    util_dmg_stats["Given UD Per Nade"] = (
        util_dmg_stats["Given UD"] / util_dmg_stats["Nades Thrown"]
    )
    util_dmg_stats["UD Per Nade"] = (
        util_dmg_stats["UD"] / util_dmg_stats["Nades Thrown"]
    )
    util_dmg_stats.sort_values(by="Given UD", ascending=False, inplace=True)
    util_dmg_stats.reset_index(drop=True, inplace=True)
    return util_dmg_stats


def flash_stats(
    flash_data: pd.DataFrame,
    grenade_data: pd.DataFrame,
    kill_data: pd.DataFrame,
    team: bool = False,
    flash_filters: Dict[str, Union[List[bool], List[str]]] = {},
    grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with flashbang statistics.

    Args:
        flash_data: A dataframe with flash data.
        grenade_data: A dataframe with grenade data.
        kill_data: A dataframe with kill data.
        team: A boolean specifying whether to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        flash_filters: A dictionary where the keys are the columns of the
            dataframe represented by flash_data to filter the flash data by
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the
            dataframe represented by grenade_data to filter the grenade data by
            and the values are lists that contain the column filters.
        kill_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with the effective flashes (EF), flash assists (FA), effective blind time (EBT), team flashes (TF), total flashes
    """
    stats = ["attackerName", "flashThrowerName", "throwerName", "Player"]
    if team:
        stats = ["attackerTeam", "flashThrowerTeam", "throwerTeam", "Team"]
    enemy_flashes = calc_stats(
        flash_data.loc[flash_data["attackerTeam"] != flash_data["playerTeam"]],
        flash_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[3], "EF"],
    )
    flash_assists = calc_stats(
        kill_data.loc[kill_data["flashThrowerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        [stats[1]],
        [stats[1]],
        [["size"]],
        [stats[3], "FA"],
    )
    blind_time = calc_stats(
        flash_data.loc[flash_data["attackerTeam"] != flash_data["playerTeam"]],
        flash_filters,
        [stats[0]],
        ["flashDuration"],
        [["sum"]],
        [stats[3], "EBT"],
    )
    team_flashes = calc_stats(
        flash_data.loc[flash_data["attackerTeam"] == flash_data["playerTeam"]],
        flash_filters,
        [stats[0]],
        [stats[0]],
        [["size"]],
        [stats[3], "TF"],
    )
    flashes_thrown = calc_stats(
        grenade_data.loc[grenade_data["grenadeType"] == "Flashbang"],
        flash_filters,
        [stats[2]],
        [stats[2]],
        [["size"]],
        [stats[3], "Flashes Thrown"],
    )
    flash_stats = enemy_flashes.merge(flash_assists, how="outer").fillna(0)
    flash_stats = flash_stats.merge(blind_time, how="outer").fillna(0)
    flash_stats = flash_stats.merge(team_flashes, how="outer").fillna(0)
    flash_stats = flash_stats.merge(flashes_thrown, how="outer").fillna(0)
    flash_stats["EF Per Throw"] = flash_stats["EF"] / flash_stats["Flashes Thrown"]
    flash_stats["EBT Per Enemy"] = flash_stats["EBT"] / flash_stats["EF"]
    flash_stats["FA"] = flash_stats["FA"].astype(int)
    flash_stats.sort_values(by="EF", ascending=False, inplace=True)
    flash_stats.reset_index(drop=True, inplace=True)
    return flash_stats


def bomb_stats(
    bomb_data: pd.DataFrame, bomb_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with bomb event statistics.

    Args:
        bomb_data: A dataframe with bomb event data.
        bomb_filters: A dictionary where the keys are the columns of the
            dataframe represented by bomb_data to filter the bomb data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with bomb plant summaries.
    """
    team_one = bomb_data["playerTeam"].unique()[0]
    team_two = bomb_data["playerTeam"].unique()[1]
    team_one_plants = calc_stats(
        bomb_data.loc[
            (bomb_data["bombAction"] == "plant") & (bomb_data["playerTeam"] == team_one)
        ],
        bomb_filters,
        ["bombSite"],
        ["bombSite"],
        [["size"]],
        ["Bombsite", f"{team_one} Plants"],
    )
    team_two_plants = calc_stats(
        bomb_data.loc[
            (bomb_data["bombAction"] == "plant") & (bomb_data["playerTeam"] == team_two)
        ],
        bomb_filters,
        ["bombSite"],
        ["bombSite"],
        [["size"]],
        ["Bombsite", f"{team_two} Plants"],
    )
    team_one_defuses = calc_stats(
        bomb_data.loc[
            (bomb_data["bombAction"] == "defuse")
            & (bomb_data["playerTeam"] == team_one)
        ],
        bomb_filters,
        ["bombSite"],
        ["bombSite"],
        [["size"]],
        ["Bombsite", f"{team_one} Defuses"],
    )
    team_two_defuses = calc_stats(
        bomb_data.loc[
            (bomb_data["bombAction"] == "defuse")
            & (bomb_data["playerTeam"] == team_two)
        ],
        bomb_filters,
        ["bombSite"],
        ["bombSite"],
        [["size"]],
        ["Bombsite", f"{team_two} Defuses"],
    )
    bomb_stats = team_one_plants.merge(team_two_defuses, how="outer").fillna(0)
    bomb_stats[f"{team_two} Defuse %"] = (
        bomb_stats[f"{team_two} Defuses"] / bomb_stats[f"{team_one} Plants"]
    )
    bomb_stats = bomb_stats.merge(team_two_plants, how="outer").fillna(0)
    bomb_stats = bomb_stats.merge(team_one_defuses, how="outer").fillna(0)
    bomb_stats[f"{team_one} Defuse %"] = (
        bomb_stats[f"{team_one} Defuses"] / bomb_stats[f"{team_two} Plants"]
    )
    bomb_stats.loc[2] = [
        "A and B",
        bomb_stats[f"{team_one} Plants"].sum(),
        bomb_stats[f"{team_two} Defuses"].sum(),
        (
            bomb_stats[f"{team_two} Defuses"].sum()
            / bomb_stats[f"{team_one} Plants"].sum()
        ),
        bomb_stats[f"{team_two} Plants"].sum(),
        bomb_stats[f"{team_one} Defuses"].sum(),
        (
            bomb_stats[f"{team_one} Defuses"].sum()
            / bomb_stats[f"{team_two} Plants"].sum()
        ),
    ]
    bomb_stats.fillna(0, inplace=True)
    bomb_stats.iloc[:, [1, 2, 4, 5]] = bomb_stats.iloc[:, [1, 2, 4, 5]].astype(int)
    return bomb_stats


def econ_stats(
    round_data: pd.DataFrame,
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with economy statistics.

    Args:
        round_data: A dataframe with round data.
        round_filters: A dictionary where the keys are the columns of the
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with round economy summaries.
    """
    ct_stats = calc_stats(
        round_data,
        round_filters,
        ["ctTeam"],
        ["ctStartEqVal", "ctRoundStartMoney", "ctSpend"],
        [["mean"], ["mean"], ["mean"]],
        ["Side", "Avg EQ Value", "Avg Cash", "Avg Spend"],
    )
    ct_stats["Side"] = ct_stats["Side"] + " CT"
    ct_buys = calc_stats(
        round_data,
        round_filters,
        ["ctTeam", "ctBuyType"],
        ["ctBuyType"],
        [["size"]],
        ["Side", "Buy Type", "Counts"],
    )
    ct_buys = ct_buys.pivot(index="Side", columns="Buy Type", values="Counts")
    ct_buys.reset_index(inplace=True)
    ct_buys.rename_axis(None, axis=1, inplace=True)
    ct_buys["Side"] = ct_buys["Side"] + " CT"
    t_stats = calc_stats(
        round_data,
        round_filters,
        ["tTeam"],
        ["tStartEqVal", "tRoundStartMoney", "tSpend"],
        [["mean"], ["mean"], ["mean"]],
        ["Side", "Avg EQ Value", "Avg Cash", "Avg Spend"],
    )
    t_stats["Side"] = t_stats["Side"] + " T"
    t_buys = calc_stats(
        round_data,
        round_filters,
        ["tTeam", "tBuyType"],
        ["tBuyType"],
        [["size"]],
        ["Side", "Buy Type", "Counts"],
    )
    t_buys = t_buys.pivot(index="Side", columns="Buy Type", values="Counts")
    t_buys.reset_index(inplace=True)
    t_buys.rename_axis(None, axis=1, inplace=True)
    t_buys["Side"] = t_buys["Side"] + " T"
    econ_buys = ct_buys.append(t_buys)
    econ_stats = ct_stats.append(t_stats)
    econ_stats = econ_buys.merge(econ_stats, how="outer")
    econ_stats.fillna(0, inplace=True)
    econ_stats.iloc[:, 1:] = econ_stats.iloc[:, 1:].astype(int)
    return econ_stats


def weapon_type(weapon: str) -> str:
    """Returns the weapon type of a weapon.

    Args:
        weapon: Weapon name

    Returns:
        A string for the weapon type (Knife, Pistol, Shotgun, SMG, Assault Rifle, Machine Gun, Sniper Rifle, Utility)
    """
    if weapon in ["Knife"]:
        return "Melee Kills"
    elif weapon in [
        "CZ-75 Auto",
        "Desert Eagle",
        "Dual Berettas",
        "Five-SeveN",
        "Glock-18",
        "P2000",
        "P250",
        "R8 Revolver",
        "Tec-9",
        "USP-S",
    ]:
        return "Pistol Kills"
    elif weapon in ["MAG-7", "Nova", "Sawed-Off", "XM1014"]:
        return "Shotgun Kills"
    elif weapon in ["MAC-10", "MP5-SD", "MP7", "MP9", "P90", "PP-Bizon", "UMP-45"]:
        return "SMG Kills"
    elif weapon in ["AK-47", "AUG", "FAMAS", "Galil AR", "M4A1-S", "M4A4", "SG 553"]:
        return "Assault Rifle Kills"
    elif weapon in ["M249", "Negev"]:
        return "Machine Gun Kills"
    elif weapon in ["AWP", "G3SG1", "SCAR-20", "SSG 08"]:
        return "Sniper Rifle Kills"
    else:
        return "Utility Kills"


def kill_breakdown(
    kill_data: pd.DataFrame,
    team: bool = False,
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with kills broken down by weapon type.

    Args:
        kill_data: A dataframe with kill data.
        team: A boolean specifying whether to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        kill_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with kill type statistics.
    """
    stats = ["attackerName", "Player"]
    if team:
        stats = ["attackerTeam", "Team"]
    kill_breakdown = kill_data.loc[
        kill_data["attackerTeam"] != kill_data["victimTeam"]
    ].copy()
    kill_breakdown["Kills Type"] = kill_breakdown.apply(
        lambda row: weapon_type(row["weapon"]), axis=1
    )
    kill_breakdown = calc_stats(
        kill_breakdown,
        kill_filters,
        [stats[0], "Kills Type"],
        [stats[0]],
        [["size"]],
        [stats[1], "Kills Type", "Kills"],
    )
    kill_breakdown = kill_breakdown.pivot(
        index=stats[1], columns="Kills Type", values="Kills"
    )
    for col in [
        "Melee Kills",
        "Pistol Kills",
        "Shotgun Kills",
        "SMG Kills",
        "Assault Rifle Kills",
        "Machine Gun Kills",
        "Sniper Rifle Kills",
        "Utility Kills",
    ]:
        if not col in kill_breakdown.columns:
            kill_breakdown.insert(0, col, 0)
        kill_breakdown[col].fillna(0, inplace=True)
        kill_breakdown[col] = kill_breakdown[col].astype(int)
    kill_breakdown["Total Kills"] = kill_breakdown.iloc[0:].sum(axis=1)
    kill_breakdown.reset_index(inplace=True)
    kill_breakdown.rename_axis(None, axis=1, inplace=True)
    kill_breakdown = kill_breakdown[
        [
            stats[1],
            "Melee Kills",
            "Pistol Kills",
            "Shotgun Kills",
            "SMG Kills",
            "Assault Rifle Kills",
            "Machine Gun Kills",
            "Sniper Rifle Kills",
            "Utility Kills",
            "Total Kills",
        ]
    ]
    kill_breakdown.sort_values(by="Total Kills", ascending=False, inplace=True)
    kill_breakdown.reset_index(drop=True, inplace=True)
    return kill_breakdown


def util_dmg_breakdown(
    damage_data: pd.DataFrame,
    grenade_data: pd.DataFrame,
    team: bool = False,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with utility damage statistics broken down by grenade
       type.

    Args:
        damage_data: A dataframe with damage data.
        grenade_data: A dataframe with grenade data.
        team: A boolean specifying whether to calculate statistics for each team
            or for each player. The default is to calculate statistics for
            each player.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the
            dataframe represented by grenade_data to filter the grenade data by
            and the values are lists that contain the column filters.

    Returns:
        A dataframe with utility damage summary.
    """
    stats = ["attackerName", "throwerName", "Player"]
    if team:
        stats = ["attackerTeam", "throwerTeam", "Team"]
    util_dmg = calc_stats(
        damage_data.loc[
            (damage_data["attackerTeam"] != damage_data["victimTeam"])
            & (
                damage_data["weapon"].isin(
                    ["HE Grenade", "Incendiary Grenade", "Molotov"]
                )
            )
        ],
        damage_filters,
        [stats[0], "weapon"],
        ["hpDamageTaken", "hpDamage"],
        [["sum"], ["sum"]],
        [stats[2], "Nade Type", "Given UD", "UD"],
    )
    nades_thrown = calc_stats(
        grenade_data.loc[
            grenade_data["grenadeType"].isin(
                ["HE Grenade", "Incendiary Grenade", "Molotov"]
            )
        ],
        grenade_filters,
        [stats[1], "grenadeType"],
        [stats[1]],
        [["size"]],
        [stats[2], "Nade Type", "Nades Thrown"],
    )
    util_dmg_breakdown = util_dmg.merge(
        nades_thrown, how="outer", on=[stats[2], "Nade Type"]
    ).fillna(0)
    util_dmg_breakdown["Given UD Per Nade"] = (
        util_dmg_breakdown["Given UD"] / util_dmg_breakdown["Nades Thrown"]
    )
    util_dmg_breakdown["UD Per Nade"] = (
        util_dmg_breakdown["UD"] / util_dmg_breakdown["Nades Thrown"]
    )
    util_dmg_breakdown.sort_values(
        by=[stats[2], "Given UD"], ascending=[True, False], inplace=True
    )
    util_dmg_breakdown.reset_index(drop=True, inplace=True)
    return util_dmg_breakdown


def win_breakdown(
    round_data: pd.DataFrame,
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a dataframe with wins broken down by round end reason.

    Args:
        round_data: A dataframe with round data.
        round_filters: A dictionary where the keys are the columns of the
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.

    Returns:
        A dataframe with round wins described by reason.
    """
    round_data_copy = round_data.copy()
    round_data_copy.replace("BombDefused", "CT Bomb Defusal Wins", inplace=True)
    round_data_copy.replace("CTWin", "CT T Elim Wins", inplace=True)
    round_data_copy.replace("TargetBombed", "T Bomb Detonation Wins", inplace=True)
    round_data_copy.replace("TargetSaved", "CT Time Expired Wins", inplace=True)
    round_data_copy.replace("TerroristsWin", "T CT Elim Wins", inplace=True)
    win_breakdown = calc_stats(
        round_data_copy,
        round_filters,
        ["winningTeam", "roundEndReason"],
        ["roundEndReason"],
        [["size"]],
        ["Team", "RoundEndReason", "Count"],
    )
    win_breakdown = win_breakdown.pivot(
        index="Team", columns="RoundEndReason", values="Count"
    ).fillna(0)
    win_breakdown.reset_index(inplace=True)
    win_breakdown.rename_axis(None, axis=1, inplace=True)
    win_breakdown["Total CT Wins"] = win_breakdown.iloc[0:][
        list(
            set.intersection(
                set(win_breakdown.columns),
                set(["CT Bomb Defusal Wins", "CT T Elim Wins", "CT Time Expired Wins"]),
            )
        )
    ].sum(axis=1)
    win_breakdown["Total T Wins"] = win_breakdown.iloc[0:][
        list(
            set.intersection(
                set(win_breakdown.columns),
                set(["T Bomb Detonation Wins", "T CT Elim Wins"]),
            )
        )
    ].sum(axis=1)
    win_breakdown["Total Wins"] = win_breakdown.iloc[0:, 0:-2].sum(axis=1)
    win_breakdown.iloc[:, 1:] = win_breakdown.iloc[:, 1:].astype(int)
    return win_breakdown


def player_box_score(
    damage_data: pd.DataFrame,
    flash_data: pd.DataFrame,
    grenade_data: pd.DataFrame,
    kill_data: pd.DataFrame,
    round_data: pd.DataFrame,
    weapon_fire_data: pd.DataFrame,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    flash_filters: Dict[str, Union[List[bool], List[str]]] = {},
    grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
    death_filters: Dict[str, Union[List[bool], List[str]]] = {},
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
    weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a player box score dataframe.

    Args:
       damage_data: A dataframe with damage data.
       flash_data: A dataframe with flash data.
       grenade_data: A dataframe with grenade data.
       kill_data: A dataframe with kill data.
       round_data: A dataframe with round data.
       weapon_fire_data: A dataframe with weapon fire data.
       damage_filters: A dictionary where the keys are the columns of the
           dataframe represented by damage_data to filter the damage data by
           and the values are lists that contain the column filters.
       flash_filters: A dictionary where the keys are the columns of the
           dataframe represented by flash_data to filter the flash data by
           and the values are lists that contain the column filters.
       grenade_filters: A dictionary where the keys are the columns of the
           dataframe represented by grenade_data to filter the grenade data by
           and the values are lists that contain the column filters.
       kill_filters: A dictionary where the keys are the columns of the
           dataframe represented by kill_data to filter the kill data by and
           the values are lists that contain the column filters.
       death_filters: A dictionary where the keys are the columns of the
           dataframe represented by kill_data to filter the death data by and
           the values are lists that contain the column filters.
       round_filters: A dictionary where the keys are the columns of the
           dataframe represented by round_data to filter the round data by and
           the values are lists that contain the column filters.
       weapon_fire_filters: A dictionary where the keys are the columns of the
           dataframe to filter the weapon fire data by and the values are lists
           that contain the column filters.

    Returns:
        A dataframe with player summaries.
    """
    k_stats = kill_stats(
        damage_data,
        kill_data,
        round_data,
        weapon_fire_data,
        damage_filters,
        kill_filters,
        death_filters,
        round_filters,
        weapon_fire_filters,
    )
    k_stats = k_stats[
        ["Player", "K", "D", "A", "FA", "HS%", "ACC%", "HS ACC%", "KDR", "KAST%"]
    ]
    adr_stats = adr(damage_data, round_data, damage_filters, round_filters)
    adr_stats = adr_stats[["Player", "Norm ADR"]]
    adr_stats.columns = ["Player", "ADR"]
    ud_stats = util_dmg(damage_data, grenade_data, damage_filters, grenade_filters)
    ud_stats = ud_stats[["Player", "UD", "UD Per Nade"]]
    f_stats = flash_stats(
        flash_data,
        grenade_data,
        kill_data,
        flash_filters,
        grenade_filters,
        kill_filters,
    )
    f_stats = f_stats[["Player", "EF", "EF Per Throw"]]
    rating_stats = rating(
        damage_data,
        kill_data,
        round_data,
        damage_filters,
        death_filters,
        kill_filters,
        round_filters,
    )
    box_score = k_stats.merge(adr_stats, how="outer").fillna(0)
    box_score = box_score.merge(ud_stats, how="outer").fillna(0)
    box_score = box_score.merge(f_stats, how="outer").fillna(0)
    box_score = box_score.merge(rating_stats, how="outer").fillna(0)
    return box_score


def team_box_score(
    damage_data: pd.DataFrame,
    flash_data: pd.DataFrame,
    grenade_data: pd.DataFrame,
    kill_data: pd.DataFrame,
    round_data: pd.DataFrame,
    weapon_fire_data: pd.DataFrame,
    damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
    flash_filters: Dict[str, Union[List[bool], List[str]]] = {},
    grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
    death_filters: Dict[str, Union[List[bool], List[str]]] = {},
    round_filters: Dict[str, Union[List[bool], List[str]]] = {},
    weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    """Returns a team box score dataframe.

    Args:
       damage_data: A dataframe with damage data.
       flash_data: A dataframe with flash data.
       grenade_data: A dataframe with grenade data.
       kill_data: A dataframe with kill data.
       round_data: A dataframe with round data.
       weapon_fire_data: A dataframe with weapon fire data.
       damage_filters: A dictionary where the keys are the columns of the
           dataframe represented by damage_data to filter the damage data by
           and the values are lists that contain the column filters.
       flash_filters: A dictionary where the keys are the columns of the
           dataframe represented by flash_data to filter the flash data by
           and the values are lists that contain the column filters.
       grenade_filters: A dictionary where the keys are the columns of the
           dataframe represented by grenade_data to filter the grenade data by
           and the values are lists that contain the column filters.
       kill_filters: A dictionary where the keys are the columns of the
           dataframe represented by kill_data to filter the kill data by and
           the values are lists that contain the column filters.
       death_filters: A dictionary where the keys are the columns of the
           dataframe represented by kill_data to filter the death data by and
           the values are lists that contain the column filters.
       round_filters: A dictionary where the keys are the columns of the
           dataframe represented by round_data to filter the round data by and
           the values are lists that contain the column filters.
       weapon_fire_filters: A dictionary where the keys are the columns of the
           dataframe to filter the weapon fire data by and the values are lists
           that contain the column filters.

    Returns:
        A dataframe with team summaries.
    """
    k_stats = kill_stats(
        damage_data,
        kill_data,
        round_data,
        weapon_fire_data,
        True,
        damage_filters,
        kill_filters,
        death_filters,
        round_filters,
        weapon_fire_filters,
    )
    acc_stats = accuracy(
        damage_data, weapon_fire_data, True, damage_filters, weapon_fire_filters
    )
    adr_stats = adr(damage_data, round_data, True, damage_filters, round_filters)
    ud_stats = util_dmg(
        damage_data, grenade_data, True, damage_filters, grenade_filters
    )
    f_stats = flash_stats(
        flash_data,
        grenade_data,
        kill_data,
        True,
        flash_filters,
        grenade_filters,
        kill_filters,
    )
    e_stats = econ_stats(round_data, round_filters)
    for index in e_stats.index:
        e_stats.iloc[index, 0] = e_stats["Side"].str.rsplit(n=1)[index][0]
        rounds = e_stats.iloc[index, 1:-4].sum()
        e_stats.iloc[index, -3:] = e_stats.iloc[index, -3:] * rounds
    e_stats = e_stats.groupby(["Side"]).sum()
    e_stats.reset_index(inplace=True)
    e_stats.iloc[:, -3:] = (
        e_stats.iloc[:, -3:] / len(filter_df(round_data, round_filters))
    ).astype(int)
    e_stats.rename(columns={"Side": "Team"}, inplace=True)
    box_score = k_stats.merge(acc_stats, how="outer")
    box_score = box_score.merge(adr_stats, how="outer")
    box_score = box_score.merge(ud_stats, how="outer")
    box_score = box_score.merge(f_stats, how="outer")
    box_score = box_score.merge(e_stats, how="outer")
    box_score = box_score.merge(
        win_breakdown(round_data, round_filters), how="outer"
    ).fillna(0)
    box_score.rename(
        columns={
            "Norm ADR": "ADR",
            "Total CT Wins": "CT Wins",
            "Total T Wins": "T Wins",
            "Total Wins": "Score",
        },
        inplace=True,
    )
    score = box_score["Score"]
    ct_wins = box_score["CT Wins"]
    t_wins = box_score["T Wins"]
    box_score.drop(["Score", "CT Wins", "T Wins"], axis=1, inplace=True)
    box_score.insert(1, "Score", score)
    box_score.insert(2, "CT Wins", ct_wins)
    box_score.insert(3, "T Wins", t_wins)
    box_score = box_score.transpose()
    box_score.columns = box_score.iloc[0]
    box_score.drop("Team", inplace=True)
    box_score.rename_axis(None, axis=1, inplace=True)
    box_score = box_score.loc[
        [
            "Score",
            "CT Wins",
            "T Wins",
            "K",
            "D",
            "A",
            "FA",
            "+/-",
            "FK",
            "HS",
            "HS%",
            "Strafe%",
            "ACC%",
            "HS ACC%",
            "ADR",
            "UD",
            "Nades Thrown",
            "UD Per Nade",
            "EF",
            "Flashes Thrown",
            "EF Per Throw",
            "EBT Per Enemy",
        ],
        :,
    ].append(box_score.iloc[31:, :])
    return box_score
