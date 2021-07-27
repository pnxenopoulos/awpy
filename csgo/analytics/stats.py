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
    if col_to_agg:
        df_copy = df_copy.groupby(col_to_groupby).agg(agg_dict).reset_index()
    df_copy.columns = col_names
    return df_copy


def kill_stats(kill_data: pd.DataFrame,
               round_data: pd.DataFrame,
               kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
               death_filters: Dict[str, Union[List[bool], List[str]]] = {},
               round_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with kill statistics.
       
    Args: 
        kill_data: A dataframe with kill data. 
        round_data: A dataframe with round data.
        kill_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.
        round_filters: A dictionary where the keys are the columns of the 
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.
    """
    kills = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                     kill_data["VictimTeam"]],
                       kill_filters, ["AttackerName"], ["AttackerName"], 
                       [["size"]], ["Player", "K"])
    deaths = calc_stats(kill_data, death_filters, ["VictimName"], 
                        ["VictimName"], [["size"]], ["Player", "D"])
    assists = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                        kill_data["VictimTeam"]) & 
                                       (kill_data["AssistedFlash"] == False)],
                         kill_filters, ["AssisterName"], ["AssisterName"], 
                         [["size"]], ["Player", "A"])
    first_kills = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]) &
                                           (kill_data["IsFirstKill"] == True)],
                             kill_filters, ["AttackerName"], ["AttackerName"], 
                             [["size"]], ["Player", "FK"])
    headshots = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                          kill_data["VictimTeam"]) & 
                                         (kill_data["IsHeadshot"] == True)], 
                           kill_filters, ["AttackerName"], ["AttackerName"], 
                           [["size"]], ["Player", "HS"])
    headshot_pct = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]], 
                              kill_filters, ["AttackerName"], ["IsHeadshot"], 
                              [["mean"]], ["Player", "HS%"])
    kill_stats = kills.merge(assists, how="outer")
    kill_stats = kill_stats.merge(deaths, how="outer")
    kill_stats["+/-"] = kill_stats["K"] - kill_stats["D"]
    kill_stats["KDR"] = kill_stats["K"] / kill_stats["D"]
    kill_stats["KPR"] = kill_stats["K"] / len(calc_stats(round_data, 
                                                         round_filters, [], [],                                                          
                                                         [], round_data.columns))
    kill_stats = kill_stats.merge(first_kills, how="outer")
    kill_stats = kill_stats.merge(headshots, how="outer")
    kill_stats = kill_stats.merge(headshot_pct, how="outer")
    kill_stats = kill_stats[["Player", "K", "D", "A", "+/-", "HS", "FK", "KDR", 
                             "KPR", "HS%"]]
    kill_stats.fillna(0, inplace=True)
    kill_stats.sort_values(by="K", ascending=False, inplace=True)
    kill_stats.reset_index(drop=True, inplace=True)
    return kill_stats


def adr(damage_data: pd.DataFrame,
        round_data: pd.DataFrame,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
        round_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:  
    """Returns a dataframe with ADR statistics.
   
    Args: 
        damage_data: A dataframe with damage data. 
        round_data: A dataframe with round data. 
        damage_filters: A dictionary where the keys are the columns of the 
            dataframe represented by damage_data to filter the damage data by 
            and the values are lists that contain the column filters.
        round_filters: A dictionary where the keys are the columns of the 
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.
    """    
    adr = calc_stats(damage_data.loc[damage_data["AttackerTeam"] != 
                                     damage_data["VictimTeam"]], damage_filters, 
                     ["AttackerName"],["HpDamage", "HpDamageTaken"], [["sum"], 
                                                                      ["sum"]],
                     ["Player", "Raw ADR", "Norm ADR"])
    adr["Raw ADR"] = adr["Raw ADR"] / len(calc_stats(round_data, round_filters, 
                                                     [], [], [], 
                                                     round_data.columns))
    adr["Norm ADR"] = adr["Norm ADR"] / len(calc_stats(round_data, round_filters, 
                                                       [], [], [], 
                                                       round_data.columns))
    adr.fillna(0, inplace=True)
    adr.sort_values(by="Raw ADR", ascending=False, inplace=True)
    adr.reset_index(drop=True, inplace=True)
    return adr


def util_dmg(damage_data: pd.DataFrame,
             grenade_data: pd.DataFrame,
             damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
             grenade_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with utility damage statistics.
    
    Args: 
        damage_data: A dataframe with damage data. 
        grenade_data: A dataframe with grenade data.
        damage_filters: A dictionary where the keys are the columns of the 
            dataframe represented by damage_data to filter the damage data by 
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the 
            dataframe represented by grenade_data to filter the grenade data by 
            and the values are lists that contain the column filters.
    """    
    util_dmg = calc_stats(damage_data.loc[(damage_data["AttackerTeam"] != 
                                           damage_data["VictimTeam"]) & 
                                          (damage_data["Weapon"].isin([ 
                                               "HE Grenade", 
                                               "Incendiary Grenade", 
                                               "Molotov"
                                          ]))], damage_filters, ["AttackerName"], 
                          ["HpDamage", "HpDamageTaken"], [["sum"], ["sum"]], 
                          ["Player", "UD", "Given UD"])
    nades_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"].isin([
                                                   "HE Grenade", 
                                                   "Incendiary Grenade", 
                                                   "Molotov"
                                               ])], grenade_filters, 
                              ["PlayerName"], ["PlayerName"], [["size"]], 
                              ["Player", "Nades Thrown"])
    util_dmg_stats = util_dmg.merge(nades_thrown, how="outer")
    util_dmg_stats["UD Per Nade"] = (util_dmg_stats["UD"] 
                                     / util_dmg_stats["Nades Thrown"])
    util_dmg_stats["Given UD Per Nade"] = (util_dmg_stats["Given UD"] 
                                           / util_dmg_stats["Nades Thrown"])
    util_dmg_stats.fillna(0, inplace=True)
    util_dmg_stats.sort_values(by="UD", ascending=False, inplace=True)
    util_dmg_stats.reset_index(drop=True, inplace=True)
    return util_dmg_stats


def flash_stats(flash_data: pd.DataFrame,
                grenade_data: pd.DataFrame,
                flash_filters: Dict[str, Union[List[bool], List[str]]] = {},
                grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:  
    """Returns a dataframe with flashbang statistics.

    Args: 
        flash_data: A dataframe with flash data. 
        grenade_data: A dataframe with grenade data.
        flash_filters: A dictionary where the keys are the columns of the 
            dataframe represented by flash_data to filter the flash data by 
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the 
            dataframe represented by grenade_data to filter the grenade data by 
            and the values are lists that contain the column filters.
    """  
    enemy_flashes = calc_stats(flash_data.loc[flash_data["AttackerTeam"] != 
                                              flash_data["PlayerTeam"]], 
                               flash_filters, ["AttackerName"], ["AttackerName"], 
                               [["size"]], ["Player", "EF"])
    team_flashes = calc_stats(flash_data.loc[flash_data["AttackerTeam"] == 
                                             flash_data["PlayerTeam"]], 
                              flash_filters, ["AttackerName"], ["AttackerName"], 
                              [["size"]], ["Player", "TF"])
    flashes_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"] == 
                                                 "Flashbang"], flash_filters, 
                                ["PlayerName"], ["PlayerName"], [["size"]], 
                                ["Player", "Flashes Thrown"])
    flash_stats = enemy_flashes.merge(team_flashes, how="outer")
    flash_stats = flash_stats.merge(flashes_thrown, how="outer")
    flash_stats["EF Per Throw"] = flash_stats["EF"] / flash_stats["Flashes Thrown"]
    flash_stats.fillna(0, inplace=True)
    flash_stats.sort_values(by="EF", ascending=False, inplace=True)
    flash_stats.reset_index(drop=True, inplace=True)
    return flash_stats


def bomb_stats(bomb_data: pd.DataFrame,
               bomb_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:  
    """Returns a dataframe with bomb event statistics.
        
    Args: 
        bomb_data: A dataframe with bomb event data. 
        bomb_filters: A dictionary where the keys are the columns of the 
            dataframe represented by bomb_data to filter the bomb data by and
            the values are lists that contain the column filters.
    """ 
    team_one = bomb_data["PlayerTeam"].unique()[0]
    team_two = bomb_data["PlayerTeam"].unique()[1]
    team_one_plants = calc_stats(bomb_data.loc[(bomb_data["BombAction"] == 
                                                "plant") & 
                                               (bomb_data["PlayerTeam"] == 
                                                team_one)], bomb_filters, 
                                 ["BombSite"], ["BombSite"], [["size"]], 
                                 ["Bombsite", f"{team_one} Plants"])
    team_two_plants = calc_stats(bomb_data.loc[(bomb_data["BombAction"] == 
                                                "plant") & 
                                               (bomb_data["PlayerTeam"] == 
                                                team_two)], bomb_filters, 
                                 ["BombSite"], ["BombSite"], [["size"]],
                                 ["Bombsite", f"{team_two} Plants"])
    team_one_defuses = calc_stats(bomb_data.loc[(bomb_data["BombAction"] == 
                                                 "defuse") & 
                                                (bomb_data["PlayerTeam"] == 
                                                 team_one)], bomb_filters, 
                                  ["BombSite"], ["BombSite"], [["size"]],
                                  ["Bombsite", f"{team_one} Defuses"])
    team_two_defuses = calc_stats(bomb_data.loc[(bomb_data["BombAction"] == 
                                                 "defuse") & 
                                                (bomb_data["PlayerTeam"] == 
                                                 team_two)], bomb_filters, 
                                  ["BombSite"], ["BombSite"], [["size"]],
                                  ["Bombsite", f"{team_two} Defuses"])
    bomb_stats = team_one_plants.merge(team_two_defuses, how="outer")
    bomb_stats[f"{team_two} Defuse %"] = (bomb_stats[f"{team_two} Defuses"] /
                                          bomb_stats[f"{team_one} Plants"])
    bomb_stats = bomb_stats.merge(team_two_plants, how="outer")
    bomb_stats = bomb_stats.merge(team_one_defuses, how="outer")
    bomb_stats[f"{team_one} Defuse %"] = (bomb_stats[f"{team_one} Defuses"] /
                                          bomb_stats[f"{team_two} Plants"])
    bomb_stats.loc[2]=["A and B", bomb_stats[f"{team_one} Plants"].sum(), 
                       bomb_stats[f"{team_two} Defuses"].sum(),
                       (bomb_stats[f"{team_two} Defuses"].sum() / 
                        bomb_stats[f"{team_one} Plants"].sum()), 
                       bomb_stats[f"{team_two} Plants"].sum(), 
                       bomb_stats[f"{team_one} Defuses"].sum(),
                       (bomb_stats[f"{team_one} Defuses"].sum() / 
                        bomb_stats[f"{team_two} Plants"].sum())] 
    bomb_stats.fillna(0, inplace=True)
    return bomb_stats


def econ_stats(round_data: pd.DataFrame,
               round_data_json: List[Dict]) -> pd.DataFrame:  
    """Returns a dataframe with economy statistics.
        
    Args: 
        round_data: A dataframe with round data. 
        round_data_json: A list of dictionaries with round data
            where each round is a dictionary. 
    """ 
    team_one = round_data_json[0]["TTeam"]
    team_two = round_data_json[0]["CTTeam"]
    team_one_T_val = 0
    team_one_CT_val = 0
    team_two_T_val = 0
    team_two_CT_val = 0
    team_one_T_spend = 0
    team_one_CT_spend = 0
    team_two_T_spend = 0
    team_two_CT_spend = 0
    first_half = 0
    second_half = 0
    team_one_T_buy = calc_stats(round_data.loc[round_data["RoundNum"] <= 15], 
                                {}, ["TBuyType"], ["TBuyType"], [["size"]], 
                                ["Side", f"{team_one} T"])
    team_one_CT_buy = calc_stats(round_data.loc[round_data["RoundNum"] > 15], {}, 
                                 ["CTBuyType"], ["CTBuyType"], [["size"]], 
                                 ["Side", f"{team_one} CT"])
    team_two_T_buy = calc_stats(round_data.loc[round_data["RoundNum"] > 15], {}, 
                                ["TBuyType"], ["TBuyType"], [["size"]], 
                                ["Side", f"{team_two} T"])
    team_two_CT_buy = calc_stats(round_data.loc[round_data["RoundNum"] < 15], {}, 
                                 ["CTBuyType"], ["CTBuyType"], [["size"]], 
                                 ["Side", f"{team_two} CT"])
    for rd in round_data_json:
        if rd["RoundNum"] <= 15:
            team_one_T_val += rd["TStartEqVal"]
            team_two_CT_val += rd["CTStartEqVal"]
            team_one_T_spend += rd["TSpend"]
            team_two_CT_spend += rd["CTSpend"]
            first_half += 1
        else:
            team_one_CT_val += rd["CTStartEqVal"]
            team_two_T_val += rd["TStartEqVal"]
            team_one_CT_spend += rd["CTSpend"]
            team_two_T_spend += rd["TSpend"]
            second_half += 1
    if first_half == 0: first_half = 1
    if second_half == 0: second_half = 1
    team_one_T_val = team_one_T_val / first_half
    team_one_CT_val = team_one_CT_val / first_half
    team_two_T_val= team_two_T_val / second_half
    team_two_CT_val = team_two_CT_val / second_half
    team_one_T_spend = team_one_T_spend / first_half
    team_one_CT_spend = team_one_CT_spend / first_half
    team_two_T_spend = team_two_T_spend / second_half
    team_two_CT_spend = team_two_CT_spend / second_half
    econ_stats = team_one_T_buy.merge(team_one_CT_buy, how="outer")    
    econ_stats = econ_stats.merge(team_two_T_buy, how="outer")    
    econ_stats = econ_stats.merge(team_two_CT_buy, how="outer") 
    econ_stats.loc[len(econ_stats)] = ["Avg EQ Value", team_one_T_val, 
                                       team_two_CT_val, team_two_T_val, 
                                       team_one_CT_val]
    econ_stats.loc[len(econ_stats)] = ["Avg Spend", team_one_T_spend, 
                                       team_two_CT_spend, team_two_T_spend, 
                                       team_one_CT_spend]
    econ_stats.fillna(0, inplace=True)
    econ_stats.iloc[:, 1:] = econ_stats.iloc[:, 1:].astype(int)
    econ_stats = econ_stats.transpose()
    econ_stats.reset_index(inplace=True)
    econ_stats.columns = econ_stats.iloc[0]
    econ_stats.drop(0, inplace=True)
    econ_stats.reset_index(drop=True, inplace=True)
    return econ_stats


def weapon_type(weapon: str) -> str:
    """Returns the weapon type of a weapon."""
    if weapon in ["Knife"]:
        return "Melee Kills"
    elif weapon in ["CZ-75 Auto", "Desert Eagle", "Dual Berettas", "Five-SeveN",
                    "Glock-18", "P2000", "P250", "R8 Revolver", "Tec-9", 
                    "USP-S"]:
        return "Pistol Kills"
    elif weapon in ["MAG-7", "Nova", "Sawed-Off", "XM1014"]:
        return "Shotgun Kills"
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


def kill_breakdown(kill_data: pd.DataFrame,
                   kill_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with kills broken down by weapon type.
        
    Args: 
        kill_data: A dataframe with kill data. 
        kill_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
    """ 
    kill_breakdown = kill_data.loc[kill_data["AttackerTeam"] != 
                                   kill_data["VictimTeam"]].copy()
    kill_breakdown["Kills Type"] = kill_breakdown.apply(lambda row: weapon_type(
                                                            row["Weapon"]), 
                                                        axis=1)
    kill_breakdown = calc_stats(kill_breakdown, kill_filters, ["AttackerName", 
                                                               "Kills Type"],
                                ["AttackerName"], [["size"]], [
                                                               "Player", 
                                                               "Kills Type", 
                                                               "Kills"
                                ])
    kill_breakdown = kill_breakdown.pivot(index="Player", columns="Kills Type",
                                         values="Kills")
    for col in ["Melee Kills", "Pistol Kills", "Shotgun Kills", "SMG Kills", 
                "Assault Rifle Kills", "Machine Gun Kills", "Sniper Rifle Kills", 
                "Utility Kills"]:
        if not col in kill_breakdown.columns:
            kill_breakdown.insert(0, col, 0)
        kill_breakdown[col].fillna(0, inplace=True)
        kill_breakdown[col] = kill_breakdown[col].astype(int)
    kill_breakdown["Total Kills"] = kill_breakdown.iloc[0:].sum(axis=1)
    kill_breakdown.reset_index(inplace=True)
    kill_breakdown = kill_breakdown.rename_axis(None, axis=1)
    kill_breakdown = kill_breakdown[["Player", "Melee Kills", "Pistol Kills",
                                     "Shotgun Kills", "SMG Kills", 
                                     "Assault Rifle Kills", "Machine Gun Kills",
                                     "Sniper Rifle Kills", "Utility Kills", 
                                     "Total Kills"]]
    kill_breakdown.sort_values(by="Total Kills", ascending=False, inplace=True)
    kill_breakdown.reset_index(drop=True, inplace=True)
    return kill_breakdown


def util_dmg_breakdown(damage_data: pd.DataFrame,
                       grenade_data: pd.DataFrame,
                       damage_filters: Dict[str, Union[List[bool], 
                                                       List[str]]] = {},
                       grenade_filters: Dict[str, Union[List[bool], 
                                                        List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with utility damage statistics broken down by grenade
       type.

    Args: 
        damage_data: A dataframe with damage data. 
        grenade_data: A dataframe with grenade data.
        damage_filters: A dictionary where the keys are the columns of the 
            dataframe represented by damage_data to filter the damage data by 
            and the values are lists that contain the column filters.
        grenade_filters: A dictionary where the keys are the columns of the 
            dataframe represented by grenade_data to filter the grenade data by 
            and the values are lists that contain the column filters.
    """    
    util_dmg = calc_stats(damage_data.loc[(damage_data["AttackerTeam"] != 
                                           damage_data["VictimTeam"]) & 
                                          (damage_data["Weapon"].isin([
                                               "HE Grenade", 
                                               "Incendiary Grenade",
                                               "Molotov"
                                          ]))], damage_filters, ["AttackerName", 
                                                                 "Weapon"], 
                          ["HpDamage", "HpDamageTaken"], [["sum"], ["sum"]], 
                          ["Player", "Nade Type", "UD", "Given UD"])
    nades_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"].isin([
                                                   "HE Grenade", 
                                                   "Incendiary Grenade", 
                                                   "Molotov"
                                               ])], grenade_filters, 
                              ["PlayerName", "GrenadeType"], ["PlayerName"], 
                              [["size"]], ["Player", "Nade Type","Nades Thrown"])
    util_dmg_breakdown = util_dmg.merge(nades_thrown, how="outer", on = 
                                        ["Player", "Nade Type"])
    util_dmg_breakdown["UD Per Nade"] = (util_dmg_breakdown["UD"] 
                                         / util_dmg_breakdown["Nades Thrown"])
    util_dmg_breakdown["Given UD Per Nade"] = (util_dmg_breakdown["Given UD"]
                                               / util_dmg_breakdown["Nades Thrown"])
    util_dmg_breakdown.fillna(0, inplace=True)
    util_dmg_breakdown.sort_values(by=["Player", "UD"], ascending=[True, False], 
                                   inplace=True)
    util_dmg_breakdown.reset_index(drop=True, inplace=True)
    return util_dmg_breakdown


def win_breakdown(round_data: pd.DataFrame,
                  round_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:     
    """Returns a dataframe with wins broken down by round end reason.
        
    Args: 
        round_data: A dataframe with round data.
        round_filters: A dictionary where the keys are the columns of the 
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.
    """ 
    win_breakdown = calc_stats(round_data, round_filters, ["WinningTeam", 
                                                           "RoundEndReason"],
                               ["RoundEndReason"], [["size"]], [
                                                                "Team", 
                                                                "RoundEndReason", 
                                                                "Count"
                               ])
    win_breakdown = win_breakdown.pivot(index="Team", columns="RoundEndReason", 
                                        values="Count")
    win_breakdown.reset_index(inplace=True)
    win_breakdown = win_breakdown.rename_axis(None, axis=1)
    win_breakdown["Total"] = win_breakdown.iloc[0:].sum(axis=1)
    return win_breakdown


def player_box_score(damage_data: pd.DataFrame,
                     flash_data: pd.DataFrame,
                     grenade_data: pd.DataFrame,
                     kill_data: pd.DataFrame,
                     round_data: pd.DataFrame,
                     damage_filters: Dict[str, Union[List[bool], 
                                                     List[str]]] = {},
                     flash_filters: Dict[str, Union[List[bool], 
                                                    List[str]]] = {},
                     grenade_filters: Dict[str, Union[List[bool], 
                                                      List[str]]] = {},
                     kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
                     death_filters: Dict[str, Union[List[bool], 
                                                    List[str]]] = {},
                     round_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a player box score dataframe.
    
     Args: 
        damage_data: A dataframe with damage data. 
        flash_data: A dataframe with flash data. 
        grenade_data: A dataframe with grenade data. 
        kill_data: A dataframe with kill data. 
        round_data: A dataframe with round data.
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
    """
    kills_df = kill_stats(kill_data, round_data, kill_filters, 
                          death_filters, round_filters)
    kills_df = kills_df[["Player", "K", "D", "A", "+/-", "KDR", "HS%"]]
    adr_df = adr(damage_data, round_data, damage_filters, round_filters)
    adr_df = adr_df[["Player", "Norm ADR"]]
    adr_df.columns = ["Player", "ADR"]
    ud_df = util_dmg(damage_data, grenade_data, damage_filters, grenade_filters)
    ud_df = ud_df[["Player", "UD", "UD Per Nade"]]
    flashes_df = flash_stats(flash_data, grenade_data, flash_filters, 
                             grenade_filters)
    flashes_df = flashes_df[["Player", "EF", "EF Per Throw"]]
    box_score = kills_df.merge(adr_df, how="outer")
    box_score = box_score[["Player", "K", "D", "A", "+/-", "KDR", "ADR", "HS%"]]
    box_score = box_score.merge(ud_df, how="outer")
    box_score = box_score.merge(flashes_df, how="outer")
    return box_score


def team_box_score(damage_data: pd.DataFrame,
                   flash_data: pd.DataFrame,
                   grenade_data: pd.DataFrame,
                   kill_data: pd.DataFrame,
                   round_data: pd.DataFrame,
                   round_data_json: List[Dict],
                   damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
                   flash_filters: Dict[str, Union[List[bool], List[str]]] = {},
                   grenade_filters: Dict[str, Union[List[bool], List[str]]] = {},
                   kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
                   death_filters: Dict[str, Union[List[bool], List[str]]] = {},
                   round_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a team box score dataframe.
    
     Args: 
        damage_data: A dataframe with damage data. 
        flash_data: A dataframe with flash data. 
        grenade_data: A dataframe with grenade data. 
        kill_data: A dataframe with kill data. 
        round_data: A dataframe with round data.
        round_data_json: A list of dictionaries with round data
            where each round is a dictionary. 
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
    """    
    kills = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                        kill_data["VictimTeam"]], kill_filters, 
                          ["AttackerTeam"], ["AttackerTeam"], [["size"]], 
                          ["Team", "K"])
    deaths = calc_stats(kill_data, death_filters, ["VictimTeam"], ["VictimTeam"], 
                        [["size"]], ["Team", "D"])
    assists = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                        kill_data["VictimTeam"]) & 
                                       (kill_data["AssistedFlash"] == False)],
                         kill_filters, ["AssisterTeam"], ["AssisterTeam"], 
                         [["size"]], ["Team", "A"])
    first_kills = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]) &
                                           (kill_data["IsFirstKill"] == True)],
                             kill_filters, ["AttackerTeam"], ["AttackerTeam"], 
                             [["size"]], ["Team", "FK"])
    headshot_pct = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]], 
                              kill_filters, ["AttackerTeam"], ["IsHeadshot"], 
                              [["mean"]], ["Team", "HS%"])
    adr = calc_stats(damage_data.loc[damage_data["AttackerTeam"] != 
                                     damage_data["VictimTeam"]], 
                     damage_filters, ["AttackerTeam"],["HpDamageTaken"], 
                     [["sum"]], ["Team", "ADR"])
    adr["ADR"] = adr["ADR"] / len(calc_stats(round_data, round_filters, [], [], 
                                             [], round_data.columns))
    util_dmg = calc_stats(damage_data.loc[(damage_data["AttackerTeam"] != 
                                           damage_data["VictimTeam"]) & 
                                          (damage_data["Weapon"].isin([ 
                                               "HE Grenade", 
                                               "Incendiary Grenade", 
                                               "Molotov"
                                          ]))], damage_filters, ["AttackerTeam"], 
                          ["HpDamage"], [["sum"]], ["Team", "UD"])
    nades_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"].isin([
                                                   "HE Grenade", 
                                                   "Incendiary Grenade", 
                                                   "Molotov"
                                               ])], grenade_filters, 
                              ["PlayerTeam"], ["PlayerTeam"], [["size"]], 
                              ["Team", "Nades Thrown"])   
    enemy_flashes = calc_stats(flash_data.loc[flash_data["AttackerTeam"] != 
                                              flash_data["PlayerTeam"]], 
                               flash_filters, ["AttackerTeam"], ["AttackerTeam"], 
                               [["size"]], ["Team", "EF"])
    flashes_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"] == 
                                                 "Flashbang"], flash_filters, 
                                ["PlayerTeam"], ["PlayerTeam"], [["size"]], 
                                ["Team", "Flashes Thrown"])
    econ_df = econ_stats(round_data, round_data_json)
    team_one = round_data_json[0]["TTeam"]
    box_score = kills.merge(deaths, how="outer")
    box_score = box_score.merge(assists, how="outer")
    box_score["+/-"] = box_score["K"] - box_score["D"]
    box_score = box_score.merge(first_kills, how="outer")
    box_score = box_score.merge(adr, how="outer")
    box_score = box_score.merge(headshot_pct, how="outer")
    box_score = box_score.merge(util_dmg, how="outer")
    box_score = box_score.merge(nades_thrown, how="outer")
    box_score["UD Per Nade"] = box_score["UD"]  / box_score["Nades Thrown"]
    box_score = box_score.merge(enemy_flashes, how="outer")
    box_score = box_score.merge(flashes_thrown, how="outer")
    box_score["EF Per Throw"] = box_score["EF"] / box_score["Flashes Thrown"]      
    if box_score.iloc[0]["Team"] == team_one:
        box_score["Avg EQ Value"] = [int(econ_df.iloc[0:2]["Avg EQ Value"].mean()), 
                                     int(econ_df.iloc[2:4]["Avg EQ Value"].mean())
                                    ] 
        box_score["Avg Spend"] = [int(econ_df.iloc[0:2]["Avg Spend"].mean()), 
                                  int(econ_df.iloc[2:4]["Avg Spend"].mean())] 
    else:
        box_score["Avg EQ Value"] = [int(econ_df.iloc[2:4]["Avg EQ Value"].mean()), 
                                     int(econ_df.iloc[0:2]["Avg EQ Value"].mean())
                                    ] 
        box_score["Avg Spend"] = [int(econ_df.iloc[2:4]["Avg Spend"].mean()), 
                                  int(econ_df.iloc[0:2]["Avg Spend"].mean())] 
    box_score = box_score.merge(win_breakdown(round_data), how="outer")
    box_score.rename(columns={"Total":"Score"}, inplace=True)
    score = box_score["Score"]
    box_score.drop("Score", axis=1, inplace=True)
    box_score.insert(1, "Score", score)
    box_score = box_score.transpose()
    box_score.columns = box_score.iloc[0]
    box_score.drop("Team", inplace=True)
    box_score = box_score.rename_axis(None, axis=1)
    return box_score