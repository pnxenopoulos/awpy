import operator
from typing import Dict, List, Tuple, Union

import pandas as pd


def extract_num_filters(filters: Dict[str, Union[List[bool], List[str]]], 
                        key: str) -> Tuple[List[str], List[float]]:
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
            raise ValueError(f"Filter(s) for column \"{key}\" must be of type " 
                             f"string.")        
        i = 0 
        sign = ""
        while i < len(index) and not index[i].isdecimal(): 
            sign += index[i] 
            end_index = i 
            i += 1
        if sign not in ('==', '!=', '<=', '>=', '<', '>'): 
            raise Exception(f"Invalid logical operator in filters for \"{key}\""
                            f" column.") 
        sign_list.append(sign) 
        try:
            val_list.append(float(index[end_index + 1:])) 
        except ValueError as ve:
            raise Exception(f"Invalid numerical value in filters for \"{key}\" "
                            f"column.") from ve    
    return sign_list, val_list 


def check_filters(df: pd.DataFrame, 
                  filters: Dict[str, Union[List[bool], List[str]]]):
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
                    raise ValueError(f"Filter(s) for column \"{key}\" must be " 
                                     f"of type boolean")
        elif df.dtypes[key] == "O":
            for index in filters[key]: 
                if not isinstance(index, str): 
                    raise ValueError(f"Filter(s) for column \"{key}\" must be " 
                                     f"of type string")
        else:
            extract_num_filters(filters, key)  

            
def num_filter_df(df: pd.DataFrame,
                  col: str,
                  sign: str,
                  val: float) -> pd.DataFrame:
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
    ops = {"==":operator.eq(df[col], val), "!=":operator.ne(df[col], val),
           "<=":operator.le(df[col], val), ">=":operator.ge(df[col], val),
           "<":operator.lt(df[col], val), ">":operator.gt(df[col], val)}
    filtered_df = df.loc[ops[sign]]
    return filtered_df


def filter_df(df: pd.DataFrame,
              filters: Dict[str, Union[List[bool], List[str]]]) -> pd.DataFrame: 
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
        if df_copy.dtypes[key] == 'bool' or df_copy.dtypes[key] == 'O': 
            df_copy = df_copy.loc[df_copy[key].isin(filters[key])]
        else:
            i = 0
            for sign in extract_num_filters(filters, key)[0]:
                val = extract_num_filters(filters, key)[1][i]
                df_copy = num_filter_df(df_copy, key, 
                                        extract_num_filters(filters, key)[0][i],
                                        val)
                i += 1
    return df_copy   


def calc_stats(df: pd.DataFrame, 
               filters: Dict[str, Union[List[bool], List[str]]], 
               col_to_groupby: List[str],
               col_to_agg: List[str],
               agg: List[List[str]],  
               col_names: List[str]) -> pd.DataFrame: 
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
    df_copy = df_copy.groupby(col_to_groupby).agg(agg_dict).reset_index()
    df_copy.columns = col_names
    return df_copy


def kdr(kill_data: pd.DataFrame,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
        death_filters: Dict[str, Union[List[bool], List[str]]] = {},
        col_names: List[str] = ["PlayerName", "Kills", "Deaths", "KDR"]
) -> pd.DataFrame:
    """Returns a dataframe with kill, death, and KDR statistics.
    
    Calls the function calc_stats to create a dataframe with kill and death 
    statistics and adds a column with KDR statistics. 
   
    Args: 
        kill_data: A dataframe with kill data. 
        kill_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.
        col_names: Column names for the returned dataframe.
    """
    kills = calc_stats(kill_data, kill_filters, ["AttackerName"], 
                       ["AttackerName"], [["size"]], ["PlayerName", "Kills"])
    deaths = calc_stats(kill_data, death_filters, ["VictimName"], 
                        ["VictimName"], [["size"]], ["PlayerName", "Deaths"])
    kdr = pd.merge(kills, deaths)
    kdr["KDR"] = kdr["Kills"] / kdr["Deaths"]
    kdr.sort_values(by="KDR", ascending=False, inplace=True)
    kdr.columns = col_names
    return kdr


def adr(round_data: pd.DataFrame,
        damage_data: pd.DataFrame,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
        col_names: List[str] = ["PlayerName", "RawADR", "NormADR"]
) -> pd.DataFrame:  
    """Returns a dataframe with ADR statistics.
 
    Calculates raw damage and normalized damage and calls the function 
    calc_stats to create a dataframe with raw ADR and normalized ADR statistics.
   
    Args: 
        round_data: A dataframe with round data. 
        damage_data: A dataframe with damage data. 
        damage_filters: A dictionary where the keys are the columns of the 
            dataframe represented by damage_data to filter the damage data by 
            and the values are lists that contain the column filters.
        col_names: Column names for the returned dataframe.
    """    
    rounds = len(round_data)
    damage_data_copy = damage_data.copy()
    damage_data_copy["RawDamage"] = (damage_data_copy["HpDamage"] 
                                     + damage_data_copy["ArmorDamage"])
    damage_data_copy["NormDamage"] = (damage_data_copy["HpDamageTaken"] 
                                      + damage_data_copy["ArmorDamage"])
    adr = calc_stats(damage_data_copy, damage_filters, ["AttackerName"],
                     ["RawDamage", "NormDamage"], [["sum"], ["sum"]],
                     ["PlayerName", "RawADR", "NormADR"])
    adr["RawADR"] = adr["RawADR"] / rounds
    adr["NormADR"] = adr["NormADR"] / rounds
    adr.sort_values(by="RawADR", ascending=False, inplace=True)
    adr.columns = col_names
    return adr


def headshot_pct(kill_data: pd.DataFrame,
                 kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
                 col_names: List[str] = ["PlayerName", "HeadshotPct"]
) -> pd.DataFrame:
    """Returns a dataframe with headshot percentage statistics.
 
    Calls the function calc_stats to create a dataframe with headshot percentage
    statistics.
   
    Args: 
        kill_data: A dataframe with kill data. 
        kill_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        col_names: Column names for the returned dataframe.
    """    
    headshot_pct = calc_stats(kill_data, kill_filters, ["AttackerName"], 
                              ["IsHeadshot"], [["mean"]], 
                              ["PlayerName", "HeadshotPct"])
    headshot_pct.sort_values(by="HeadshotPct", ascending=False, inplace=True)
    headshot_pct.columns = col_names
    return headshot_pct


def util_dmg(damage_data: pd.DataFrame,
             grenade_data: pd.DataFrame,
             damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
             grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
             col_names: List[str] = ["PlayerName", "UtilityDamage",
                                     "NadesThrown","DamagePerNade"]
) -> pd.DataFrame:
    """Returns a dataframe with utility damage statistics.
    Calculates raw damage and and calls the function calc_stats to create a 
    a dataframe with utility damage, grenades thrown, and damage per grenade 
    thrown statistics.
   
    Args: 
        damage_data: A dataframe with damage data. 
        grenade_data: A dataframe with grenade data.
        damage_filters: A dictionary where the keys are the columns of the 
            dataframe represented by damage_data to filter the damage data by 
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the 
            dataframe represented by grenade_data to filter the grende data by 
            and the values are lists that contain the column filters.
        col_names: Column names for the returned dataframe.
    """    
    damage_data_copy = damage_data.loc[damage_data["Weapon"].isin(
        ["HE Grenade", "Incendiary Grendade", "Molotov"])]
    damage_data_copy["RawDamage"] = (damage_data_copy["HpDamage"] 
                                     + damage_data_copy["ArmorDamage"])
    util_dmg = calc_stats(damage_data_copy, damage_filters, ["AttackerName"], 
                          ["RawDamage"], [["sum"]], 
                          ["PlayerName", "UtilityDamage"])
    grenade_data_copy = grenade_data.loc[grenade_data["GrenadeType"].isin(
        ["HE Grenade", "Incendiary Grendade", "Molotov"])]
    nades_thrown = calc_stats(grenade_data_copy, grenade_filters, ["PlayerName"], 
                              ["PlayerName"], [["size"]],  
                              ["PlayerName", "NadesThrown"])
    util_dmg_stats = pd.merge(util_dmg, nades_thrown)
    util_dmg_stats["DmgPerNade"] = (util_dmg_stats["UtilityDamage"] 
                                    / util_dmg_stats["NadesThrown"])
    util_dmg_stats.sort_values(by="UtilityDamage", ascending=False, inplace=True)
    util_dmg_stats.columns = col_names
    return util_dmg_stats


def weapon_type(weapon: str) -> str:
    """Returns the weapon type of a weapon."""
    if weapon in ["Knife"]:
        return "Melee Kills"
    elif weapon in ["CZ-75 Auto", "Desert Eagle", "Dual Berettas", "Five-SeveN",
                    "Glock-18", "P2000", "P250", "R8 Revolver", "Tec-9", 
                    "USP-S"]:
        return "Pistol Kills"
    elif weapon in ["MAG-7", "Nova", "Sawed-Off", "XM1014"]:
        return "Shotgun"
    elif weapon in ["MAC-10", "MP5-SD", "MP7", "MP9", "P90", "PP-Bizon",
                    "UMP-45"]:
        return "SMG Kills"
    elif weapon in ["AK-47", "AUG", "FAMAS", "Galil AR", "M4A1-S", "M4A4",
                    "SG 553"]:
        return "Assault Rifle Kills"
    elif weapon in ["M249", "Negev"]:
        return "Machine Gun Kills"
    elif weapon in ["AWP", "G3SG1", "SCAR-20", "SSG 08"]:
        return "Sniper Rifle Kills"
    else:
        return "Utility Kills"


def kills_by_weapon_type(kill_data: pd.DataFrame,
                         kill_filters: Dict[str, Union[List[bool], 
                                                       List[str]]] = {},
                         col_names: List[str] = ["Melee Kills", "Pistol Kills",
                                                 "Shotgun Kills", "SMG Kills",
                                                 "Assault Rifle Kills",
                                                 "Machine Gun Kills",
                                                 "Sniper Rifle Kills",
                                                 "Utility Kills", "Total Kills"]
) -> pd.DataFrame:
    """Returns a dataframe with kills by weapon type statistics.
    
    Calls the function weapon_type to determine the weapon type for each kill
    and calls the function calc_stats to create a dataframe with kills by weapon
    type statistics.
    
    Args: 
        kill_data: A dataframe with kill data. 
        kill_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        col_names: Column names for the returned dataframe.
    """ 
    kills_by_weapon_type = kill_data.copy()
    kills_by_weapon_type["Kills Type"] = kills_by_weapon_type.apply(
        lambda row: weapon_type(row["Weapon"]), axis=1)
    kills_by_weapon_type = calc_stats(kills_by_weapon_type, kill_filters,
                                      ["AttackerName", "Kills Type"],
                                      ["AttackerName"], [["size"]],
                                      ["PlayerName", "Kills Type", "Kills"])
    kills_by_weapon_type = kills_by_weapon_type.pivot(index="PlayerName", 
                                                      columns="Kills Type", 
                                                      values="Kills")
    for col in ["Melee Kills", "Pistol Kills", "Shotgun Kills", "SMG Kills", 
                "Assault Rifle Kills", "Machine Gun Kills", 
                "Sniper Rifle Kills", "Utility Kills"]:
        if not col in kills_by_weapon_type.columns:
            kills_by_weapon_type.insert(0, col, 0)
        kills_by_weapon_type[col] = kills_by_weapon_type[col].fillna(0)
        kills_by_weapon_type[col] = kills_by_weapon_type[col].astype(int)
    kills_by_weapon_type["Total Kills"] = kills_by_weapon_type.iloc[
        0:kills_by_weapon_type.shape[0]].sum(axis=1)
    kills_by_weapon_type.reset_index(inplace=True)
    kills_by_weapon_type = kills_by_weapon_type.rename_axis(None, axis=1)
    kills_by_weapon_type = kills_by_weapon_type[["Melee Kills", "Pistol Kills",
                                                 "Shotgun Kills", "SMG Kills",
                                                 "Assault Rifle Kills",
                                                 "Machine Gun Kills",
                                                 "Sniper Rifle Kills",
                                                 "Utility Kills", "Total Kills"]]
    kills_by_weapon_type.columns = col_names
    return kills_by_weapon_type


def player_box_score():
    raise NotImplementedError
    
    
def team_box_score():
    raise NotImplementedError