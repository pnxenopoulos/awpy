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


def accuracy(damage_data: pd.DataFrame,
             round_data_json: List[Dict],
             damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
             weapon_fires_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with accuracy statistics.
        
    Args: 
        damage_data: A dataframe with damage data.
        round_data_json: A list of dictionaries with round data
            where each round is a dictionary. 
        damage_filters: A dictionary where the keys are the columns of the 
            dataframe represented by damage_data to filter the damage data by 
            and the values are lists that contain the column filters.
        weapon_fires_filters: A dictionary where the keys are the columns of the 
            dataframe represented by weapon_fires to filter the weapon fire data 
            by and the values are lists that contain the column filters.
    """ 
    weapon_fires = pd.DataFrame.from_dict(round_data_json[0]["WeaponFires"][0:])
    weapon_fires["RoundNum"] = 1
    for rd in round_data_json[1:]:
        rd_end = len(weapon_fires)
        weapon_fires = weapon_fires.append(pd.DataFrame.from_dict(
            rd["WeaponFires"][0:]))
        weapon_fires["RoundNum"][rd_end:] = rd["RoundNum"]              
    weapon_fires.reset_index(drop=True, inplace=True)
    weapon_fires = calc_stats(weapon_fires, weapon_fires_filters, ["PlayerName"], 
                              ["PlayerName"], [["size"]], ["Player", 
                                                           "Weapon Fires"])
    hits = calc_stats(damage_data, damage_filters, ["AttackerName"], 
                      ["AttackerName"], [["size"]], ["Player", "Hits"])
    headshots = calc_stats(damage_data.loc[damage_data["HitGroup"] == "Head"], 
                           damage_filters, ["AttackerName"], ["AttackerName"], 
                           [["size"]], ["Player", "Headshots"])
    acc = weapon_fires.merge(hits, how="outer").fillna(0)
    acc = acc.merge(headshots, how="outer").fillna(0)
    acc["ACC%"] = acc["Hits"] / acc["Weapon Fires"]
    acc["HS ACC%"] = acc["Headshots"] / acc["Weapon Fires"]
    acc = acc[["Player", "Weapon Fires", "ACC%", "HS ACC%"]]
    acc.sort_values(by="ACC%", ascending=False, inplace=True)
    acc.reset_index(drop=True, inplace=True)
    return acc


def kast(kill_data: pd.DataFrame, 
         kast_string: str = "KAST", 
         kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
         death_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with KAST statistics.
    
    Args: 
        kill_data: A dataframe with kill data. 
        kast_string: A string specifying which combination of KAST statistics 
            to use. 
        kill_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the 
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.
    """
    columns = ["Player", f"{kast_string.upper()}%"]
    kast_counts = {}
    kast_rounds = {}
    for stat in kast_string.upper():
        columns.append(stat)
    killers = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                       kill_data["VictimTeam"]], 
                         kill_filters, ["RoundNum"], ["AttackerName"], 
                         [["sum"]], ["RoundNum", "Killers"])
    victims = calc_stats(kill_data, kill_filters, ["RoundNum"], ["VictimName"], 
                         [["sum"]], ["RoundNum", "Victims"])
    assisters = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                          kill_data["VictimTeam"]) & 
                                         (kill_data["AssistedFlash"] == 
                                          False)].fillna(""), kill_filters, 
                           ["RoundNum"], ["AssisterName"], [["sum"]], 
                           ["RoundNum","Assisters"])
    traded = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                       kill_data["VictimTeam"]) & 
                                      (kill_data["IsTrade"] == 
                                       True)].fillna(""), kill_filters, 
                        ["RoundNum"], ["PlayerTradedName"], [["sum"]],
                        ["RoundNum", "Traded"])
    kast_data = killers.merge(assisters, how="outer").fillna("")
    kast_data = kast_data.merge(victims, how="outer").fillna("")
    kast_data = kast_data.merge(traded, how="outer").fillna("")
    for player in kill_data["AttackerName"].unique():
        kast_counts[player] = [[0, 0, 0, 0] for i in range(len(kast_data))]
        kast_rounds[player] = [0, 0, 0, 0, 0] 
    for rd in kast_data.index:
        for player in kast_counts:
            if "K" in  kast_string.upper():
                kast_counts[player][rd][0] = kast_data.iloc[rd]["Killers"].count(
                    player)
                kast_rounds[player][1] += kast_data.iloc[rd]["Killers"].count(
                    player)
            if "A" in kast_string.upper():
                kast_counts[player][rd][1] = kast_data.iloc[rd]["Assisters"].count(
                    player) 
                kast_rounds[player][2] += kast_data.iloc[rd]["Assisters"].count(
                    player)
            if "S" in kast_string.upper(): 
                if player not in kast_data.iloc[rd]["Victims"]:
                    kast_counts[player][rd][2] = 1 
                    kast_rounds[player][3] += 1
            if "T" in kast_string.upper():
                kast_counts[player][rd][3] = kast_data.iloc[rd]["Traded"].count(
                    player)  
                kast_rounds[player][4] += kast_data.iloc[rd]["Traded"].count(
                    player)
    for player in kast_rounds:
        for rd in kast_counts[player]:
            if any(rd):
                kast_rounds[player][0] += 1
        kast_rounds[player][0] /= len(kast_data)
    kast = pd.DataFrame.from_dict(kast_rounds, orient='index').reset_index()
    kast.columns = ["Player", f"{kast_string.upper()}%", "K", "A", "S", "T"]
    kast = kast[columns]
    kast.fillna(0, inplace=True)
    kast.sort_values(by=f"{kast_string.upper()}%", ascending=False, inplace=True)
    kast.reset_index(drop=True, inplace=True)
    return kast


def kill_stats(damage_data: pd.DataFrame,
               kill_data: pd.DataFrame,
               round_data: pd.DataFrame,
               round_data_json: List[Dict],
               damage_filters: Dict[str, Union[List[bool], List[str]]] = {},
               kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
               death_filters: Dict[str, Union[List[bool], List[str]]] = {},
               round_filters: Dict[str, Union[List[bool], List[str]]] = {},
               weapon_fires_filters: Dict[str, Union[List[bool], 
                                                     List[str]]] = {}
) -> pd.DataFrame:
    """Returns a dataframe with kill statistics.
       
    Args: 
        damage_data: A dataframe with damage data.
        kill_data: A dataframe with kill data. 
        round_data: A dataframe with round data.
        round_data_json: A list of dictionaries with round data
            where each round is a dictionary.
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
        weapon_fires_filters: A dictionary where the keys are the columns of the 
            dataframe represented by weapon_fires to filter the weapon fire data 
            by and the values are lists that contain the column filters.
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
    first_deaths = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]) &
                                           (kill_data["IsFirstKill"] == True)],
                             kill_filters, ["VictimName"], ["VictimName"], 
                             [["size"]], ["Player", "FD"])
    headshots = calc_stats(kill_data.loc[(kill_data["AttackerTeam"] != 
                                          kill_data["VictimTeam"]) & 
                                         (kill_data["IsHeadshot"] == True)], 
                           kill_filters, ["AttackerName"], ["AttackerName"], 
                           [["size"]], ["Player", "HS"])
    headshot_pct = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]], 
                              kill_filters, ["AttackerName"], ["IsHeadshot"], 
                              [["mean"]], ["Player", "HS%"])
    acc_stats = accuracy(damage_data, round_data_json, damage_filters,
                         weapon_fires_filters)
    kast_stats = kast(kill_data, "KAST", kill_filters, death_filters)
    kill_stats = kills.merge(assists, how="outer").fillna(0)
    kill_stats = kill_stats.merge(deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(first_kills, how="outer").fillna(0)
    kill_stats = kill_stats.merge(first_deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(headshots, how="outer").fillna(0)
    kill_stats = kill_stats.merge(headshot_pct, how="outer").fillna(0)
    kill_stats = kill_stats.merge(acc_stats, how="outer").fillna(0)
    kill_stats = kill_stats.merge(kast_stats, how="outer").fillna(0)
    kill_stats["+/-"] = kill_stats["K"] - kill_stats["D"]
    kill_stats["KDR"] = kill_stats["K"] / kill_stats["D"]
    kill_stats["KPR"] = kill_stats["K"] / len(calc_stats(round_data, 
                                                         round_filters, [], [],                                                          
                                                         [], round_data.columns))
    kill_stats["FK +/-"] = kill_stats["FK"] - kill_stats["FD"]
    kill_stats[["K", "D", "A", "+/-", "FK", "FK +/-", "T", "HS"]] = kill_stats[[
        "K", "D", "A", "+/-", "FK", "FK +/-", "T", "HS"]].astype(int)
    kill_stats["HS%"] = kill_stats["HS%"].astype(float)
    kill_stats = kill_stats[["Player", "K", "D", "A", "+/-", "FK", "FK +/-", 
                             "T", "HS", "HS%", "ACC%", "HS ACC%", "KDR", "KPR", 
                             "KAST%"]]
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
                     ["AttackerName"],["HpDamageTaken", "HpDamage"], [["sum"], 
                                                                      ["sum"]],
                     ["Player", "Norm ADR", "Raw ADR"])
    adr["Norm ADR"] = adr["Norm ADR"] / len(calc_stats(round_data, round_filters, 
                                                       [], [], [], 
                                                       round_data.columns))
    adr["Raw ADR"] = adr["Raw ADR"] / len(calc_stats(round_data, round_filters, 
                                                     [], [], [], 
                                                     round_data.columns))
    adr.sort_values(by="Norm ADR", ascending=False, inplace=True)
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
                          ["HpDamageTaken", "HpDamage"], [["sum"], ["sum"]], 
                          ["Player", "Given UD", "UD"])
    nades_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"].isin([
                                                   "HE Grenade", 
                                                   "Incendiary Grenade", 
                                                   "Molotov"
                                               ])], grenade_filters, 
                              ["PlayerName"], ["PlayerName"], [["size"]], 
                              ["Player", "Nades Thrown"])
    util_dmg_stats = util_dmg.merge(nades_thrown, how="outer").fillna(0)
    util_dmg_stats["Given UD Per Nade"] = (util_dmg_stats["Given UD"] 
                                           / util_dmg_stats["Nades Thrown"])
    util_dmg_stats["UD Per Nade"] = (util_dmg_stats["UD"] 
                                     / util_dmg_stats["Nades Thrown"])
    util_dmg_stats.sort_values(by="Given UD", ascending=False, inplace=True)
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
    flash_stats = enemy_flashes.merge(team_flashes, how="outer").fillna(0)
    flash_stats = flash_stats.merge(flashes_thrown, how="outer").fillna(0)
    flash_stats["EF Per Throw"] = flash_stats["EF"] / flash_stats["Flashes Thrown"]
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
    bomb_stats = team_one_plants.merge(team_two_defuses, 
                                       how="outer").fillna(0)
    bomb_stats[f"{team_two} Defuse %"] = (bomb_stats[f"{team_two} Defuses"] 
                                         / bomb_stats[f"{team_one} Plants"])
    bomb_stats = bomb_stats.merge(team_two_plants, how="outer").fillna(0)
    bomb_stats = bomb_stats.merge(team_one_defuses, how="outer").fillna(0)
    bomb_stats[f"{team_one} Defuse %"] = (bomb_stats[f"{team_one} Defuses"] 
                                         / bomb_stats[f"{team_two} Plants"])
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
               round_data_json: List[Dict],
               round_filters: Dict[str, Union[List[bool], List[str]]] = {}
) -> pd.DataFrame:  
    """Returns a dataframe with economy statistics.
        
    Args: 
        round_data: A dataframe with round data. 
        round_data_json: A list of dictionaries with round data
            where each round is a dictionary. 
        round_filters: A dictionary where the keys are the columns of the 
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.
    """ 
    team_one = round_data_json[0]["CTTeam"]
    team_one_CT_val = 0
    team_one_T_val = 0
    team_one_CT_cash = 0        
    team_one_T_cash = 0
    team_one_CT_spend = 0
    team_one_T_spend = 0
    team_two = round_data_json[0]["TTeam"]
    team_two_CT_val = 0
    team_two_T_val = 0
    team_two_CT_cash = 0
    team_two_T_cash = 0
    team_two_CT_spend = 0
    team_two_T_spend = 0
    first_half = 0
    second_half = 0
    filtered_round_data_json = []
    team_one_CT_buy = calc_stats(round_data.loc[round_data["RoundNum"] <= 15], 
                                 round_filters, ["CTBuyType"], ["CTBuyType"], 
                                 [["size"]], ["Side", f"{team_one} CT"])
    team_one_T_buy = calc_stats(round_data.loc[round_data["RoundNum"] > 15], 
                                round_filters, ["TBuyType"], ["TBuyType"], 
                                [["size"]], ["Side", f"{team_one} T"])
    team_two_CT_buy = calc_stats(round_data.loc[round_data["RoundNum"] > 15],
                                 round_filters, ["CTBuyType"], ["CTBuyType"], 
                                 [["size"]], ["Side", f"{team_two} CT"])
    team_two_T_buy = calc_stats(round_data.loc[round_data["RoundNum"] <= 15],
                                round_filters, ["TBuyType"], ["TBuyType"], 
                                [["size"]], ["Side", f"{team_two} T"])
    rounds = filter_df(round_data, round_filters)["RoundNum"].unique()
    for rd in rounds:
        filtered_round_data_json.append(round_data_json[rd-1])
    for rd in filtered_round_data_json:
        if rd["RoundNum"] <= 15:
            team_one_CT_val += rd["CTStartEqVal"]
            team_one_CT_cash += rd["CTRoundStartMoney"]
            team_one_CT_spend += rd["CTSpend"]
            team_two_T_val += rd["TStartEqVal"]
            team_two_T_cash += rd["TRoundStartMoney"]
            team_two_T_spend += rd["TSpend"]
            first_half += 1
        else:                                          
            team_one_T_val += rd["TStartEqVal"]
            team_one_T_cash += rd["TRoundStartMoney"]
            team_one_T_spend += rd["TSpend"]
            team_two_CT_val += rd["CTStartEqVal"]
            team_two_CT_cash += rd["CTRoundStartMoney"]
            team_two_CT_spend += rd["CTSpend"]
            second_half += 1
    if first_half == 0: first_half = 1
    if second_half == 0: second_half = 1
    team_one_CT_val /= first_half
    team_one_CT_cash /= first_half
    team_one_CT_spend /= first_half
    team_one_T_val /= second_half
    team_one_T_cash /= second_half
    team_one_T_spend /= second_half
    team_two_CT_val /= second_half
    team_two_CT_cash /= second_half
    team_two_CT_spend /= second_half
    team_two_T_val /= first_half
    team_two_T_cash /= first_half
    team_two_T_spend /= first_half
    econ_stats = team_one_CT_buy.merge(team_one_T_buy, how="outer").fillna(0)    
    econ_stats = econ_stats.merge(team_two_CT_buy, how="outer").fillna(0)  
    econ_stats = econ_stats.merge(team_two_T_buy, how="outer").fillna(0) 
    econ_stats.loc[len(econ_stats)] = ["Avg EQ Value", team_one_CT_val, 
                                       team_one_T_val, team_two_CT_val, 
                                       team_two_T_val]
    econ_stats.loc[len(econ_stats)] = ["Avg Cash", team_one_CT_cash, 
                                       team_one_T_cash, team_two_CT_cash, 
                                       team_two_T_cash]
    econ_stats.loc[len(econ_stats)] = ["Avg Spend", team_one_CT_spend, 
                                       team_one_T_spend, team_two_CT_spend, 
                                       team_two_T_spend]
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
                          ["HpDamageTaken", "HpDamage"], [["sum"], ["sum"]], 
                          ["Player", "Nade Type", "Given UD", "UD"])
    nades_thrown = calc_stats(grenade_data.loc[grenade_data["GrenadeType"].isin([
                                                   "HE Grenade", 
                                                   "Incendiary Grenade", 
                                                   "Molotov"
                                               ])], grenade_filters, 
                              ["PlayerName", "GrenadeType"], ["PlayerName"], 
                              [["size"]], ["Player", "Nade Type","Nades Thrown"])
    util_dmg_breakdown = util_dmg.merge(nades_thrown, how="outer", on = 
                                        ["Player", "Nade Type"]).fillna(0)
    util_dmg_breakdown["Given UD Per Nade"] = (util_dmg_breakdown["Given UD"]
                                               / util_dmg_breakdown["Nades Thrown"])
    util_dmg_breakdown["UD Per Nade"] = (util_dmg_breakdown["UD"] 
                                         / util_dmg_breakdown["Nades Thrown"])
    util_dmg_breakdown.sort_values(by=["Player", "Given UD"], ascending=[True, False], 
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
    round_data_copy = round_data.copy()
    round_data_copy.replace("BombDefused", "CT Bomb Defusal Wins", inplace=True)
    round_data_copy.replace("CTWin", "CT T Elim Wins", inplace=True)
    round_data_copy.replace("TargetBombed", "T Bomb Detonation Wins", inplace=True)
    round_data_copy.replace("TargetSaved", "CT Time Expired Wins", inplace=True)
    round_data_copy.replace("TerroristsWin", "T CT Elim Wins", inplace=True)
    win_breakdown = calc_stats(round_data_copy, round_filters, ["WinningTeam", 
                                                           "RoundEndReason"],
                               ["RoundEndReason"], [["size"]], [
                                                                "Team", 
                                                                "RoundEndReason", 
                                                                "Count"
                               ])
    win_breakdown = win_breakdown.pivot(index="Team", columns="RoundEndReason", 
                                        values="Count").fillna(0)
    win_breakdown.reset_index(inplace=True)
    win_breakdown = win_breakdown.rename_axis(None, axis=1)
    win_breakdown["Total CT Wins"] = win_breakdown.iloc[0:][list(
        set.intersection(set(win_breakdown.columns), 
                         set(["CT Bomb Defusal Wins", "CT T Elim Wins", 
                              "CT Time Expired Wins"])))].sum(axis=1)
    win_breakdown["Total T Wins"] =  win_breakdown.iloc[0:][list(
        set.intersection(set(win_breakdown.columns), 
                         set(["T Bomb Detonation Wins", "T CT Elim Wins"])))
        ].sum(axis=1)
    win_breakdown["Total Wins"] = win_breakdown.iloc[0:, 0:-2].sum(axis=1)
    win_breakdown.iloc[:, 1:] = win_breakdown.iloc[:, 1:].astype(int)
    return win_breakdown


def player_box_score(damage_data: pd.DataFrame,
                     flash_data: pd.DataFrame,
                     grenade_data: pd.DataFrame,
                     kill_data: pd.DataFrame,
                     round_data: pd.DataFrame,
                     round_data_json: List[Dict],
                     damage_filters: Dict[str, Union[List[bool], 
                                                     List[str]]] = {},
                     flash_filters: Dict[str, Union[List[bool], 
                                                    List[str]]] = {},
                     grenade_filters: Dict[str, Union[List[bool], 
                                                      List[str]]] = {},
                     kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
                     death_filters: Dict[str, Union[List[bool], 
                                                    List[str]]] = {},
                     round_filters: Dict[str, Union[List[bool], List[str]]] = {},
                     weapon_fires_filters: Dict[str, Union[List[bool], 
                                                           List[str]]] = {}
) -> pd.DataFrame:
    """Returns a player box score dataframe.
    
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
        weapon_fires_filters: A dictionary where the keys are the columns of the 
            dataframe to filter the weapon fire data by and the values are lists 
            that contain the column filters.
    """
    k_stats = kill_stats(damage_data, kill_data, round_data, round_data_json, 
                         kill_filters, death_filters, round_filters, 
                         weapon_fires_filters)
    k_stats = k_stats[["Player", "K", "D", "A", "HS%", "ACC%", "HS ACC%", "KDR", 
                       "KAST%"]]
    adr_stats = adr(damage_data, round_data, damage_filters, round_filters)
    adr_stats = adr_stats[["Player", "Norm ADR"]]
    adr_stats.columns = ["Player", "ADR"]
    ud_stats = util_dmg(damage_data, grenade_data, damage_filters, grenade_filters)
    ud_stats = ud_stats[["Player", "UD", "UD Per Nade"]]
    f_stats = flash_stats(flash_data, grenade_data, flash_filters, 
                          grenade_filters)
    f_stats = f_stats[["Player", "EF", "EF Per Throw"]]
    box_score = k_stats.merge(adr_stats, how="outer").fillna(0)
    box_score = box_score.merge(ud_stats, how="outer").fillna(0)
    box_score = box_score.merge(f_stats, how="outer").fillna(0)
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
                   round_filters: Dict[str, Union[List[bool], List[str]]] = {},
                   weapon_fires_filters: Dict[str, Union[List[bool], 
                                                         List[str]]] = {}
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
        weapon_fires_filters: A dictionary where the keys are the columns of the 
            dataframe to filter the weapon fire data by and the values are lists 
            that contain the column filters.
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
    adr = calc_stats(damage_data.loc[damage_data["AttackerTeam"] != 
                                     damage_data["VictimTeam"]], 
                     damage_filters, ["AttackerTeam"],["HpDamageTaken"], 
                     [["sum"]], ["Team", "ADR"])
    adr["ADR"] = adr["ADR"] / len(calc_stats(round_data, round_filters, [], [], 
                                             [], round_data.columns))
    headshot_pct = calc_stats(kill_data.loc[kill_data["AttackerTeam"] != 
                                            kill_data["VictimTeam"]], 
                              kill_filters, ["AttackerTeam"], ["IsHeadshot"], 
                              [["mean"]], ["Team", "HS%"])
    weapon_fires = pd.DataFrame.from_dict(round_data_json[0]["WeaponFires"][0:])
    weapon_fires["RoundNum"] = 1
    for rd in round_data_json[1:]:
        rd_end = len(weapon_fires)
        weapon_fires = weapon_fires.append(pd.DataFrame.from_dict(
            rd["WeaponFires"][0:]))
        weapon_fires["RoundNum"][rd_end:] = rd["RoundNum"]              
    weapon_fires.reset_index(drop=True, inplace=True)
    weapon_fires = calc_stats(weapon_fires, weapon_fires_filters, ["PlayerTeam"], 
                              ["PlayerTeam"], [["size"]], ["Team", 
                                                           "Weapon Fires"])
    hits = calc_stats(damage_data, weapon_fires_filters, ["AttackerTeam"], 
                      ["AttackerTeam"], [["size"]], ["Team", "Hits"])
    headshots = calc_stats(damage_data.loc[damage_data["HitGroup"] == "Head"], 
                           weapon_fires_filters, ["AttackerTeam"], 
                           ["AttackerTeam"], [["size"]], ["Team", "Headshots"])
    acc = weapon_fires.merge(hits, how="outer").fillna(0)
    acc = acc.merge(headshots, how="outer").fillna(0)
    acc["ACC%"] = acc["Hits"] / acc["Weapon Fires"]
    acc["HS ACC%"] = acc["Headshots"] / acc["Weapon Fires"]
    acc = acc[["Team", "ACC%", "HS ACC%"]]
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
    econ = econ_stats(round_data, round_data_json, round_filters)
    team_one = round_data_json[0]["CTTeam"]
    box_score = kills.merge(deaths, how="outer").fillna(0)
    box_score = box_score.merge(assists, how="outer").fillna(0)
    box_score["+/-"] = box_score["K"] - box_score["D"]
    box_score = box_score.merge(first_kills, how="outer").fillna(0)
    box_score = box_score.merge(adr, how="outer").fillna(0)
    box_score = box_score.merge(headshot_pct, how="outer").fillna(0)
    box_score = box_score.merge(acc, how="outer").fillna(0)
    box_score = box_score.merge(util_dmg, how="outer").fillna(0)
    box_score = box_score.merge(nades_thrown, how="outer").fillna(0)
    box_score["UD Per Nade"] = box_score["UD"]  / box_score["Nades Thrown"]
    box_score = box_score.merge(enemy_flashes, how="outer").fillna(0)
    box_score = box_score.merge(flashes_thrown, how="outer").fillna(0)
    box_score["EF Per Throw"] = box_score["EF"] / box_score["Flashes Thrown"]      
    if box_score.iloc[0]["Team"] == team_one:
        for buy_type in econ.columns[1:-3]:
            box_score[buy_type] = [econ.iloc[0:2][buy_type].sum(), 
                                   econ.iloc[2:][buy_type].sum()]
        box_score["Avg EQ Value"] = [int(econ.iloc[0:2]["Avg EQ Value"].mean()), 
                                     int(econ.iloc[2:]["Avg EQ Value"].mean())] 
        box_score["Avg Cash"] = [int(econ.iloc[0:2]["Avg Cash"].mean()), 
                                 int(econ.iloc[2:]["Avg Cash"].mean())] 
        box_score["Avg Spend"] = [int(econ.iloc[0:2]["Avg Spend"].mean()), 
                                  int(econ.iloc[2:]["Avg Spend"].mean())] 
    else:
        for buy_type in econ.columns[1:-3]:
            box_score[buy_type] = [econ.iloc[2:][buy_type].sum(), 
                                   econ.iloc[0:2][buy_type].sum()]
        box_score["Avg EQ Value"] = [int(econ.iloc[2:]["Avg EQ Value"].mean()), 
                                     int(econ.iloc[0:2]["Avg EQ Value"].mean())] 
        box_score["Avg Cash"] = [int(econ.iloc[2:]["Avg Cash"].mean()), 
                                 int(econ.iloc[0:2]["Avg Cash"].mean())] 
        box_score["Avg Spend"] = [int(econ.iloc[2:]["Avg Spend"].mean()), 
                                  int(econ.iloc[0:2]["Avg Spend"].mean())] 
    box_score = box_score.merge(win_breakdown(round_data), how="outer").fillna(0)
    box_score.rename(columns={"Total CT Wins":"CT Wins", "Total T Wins":"T Wins", 
                              "Total Wins":"Score"}, inplace=True)
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
    box_score = box_score.rename_axis(None, axis=1)
    return box_score