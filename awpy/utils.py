""" Util functions for csgo package
"""

import re
import subprocess
import pandas as pd
from awpy.types import Area


class AutoVivification(dict):
    """Implementation of perl's autovivification feature. Stolen from https://stackoverflow.com/questions/651794/whats-the-best-way-to-initialize-a-dict-of-dicts-in-python"""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


def check_go_version() -> bool:
    """Function to check the Golang version of the current machine, returns True if greater than 1.17.0

    Returns:
        bool whether the found go version is recent enough"""
    try:
        proc = subprocess.Popen(["go", "version"], stdout=subprocess.PIPE)
        parsed_resp = (
            proc.stdout.read().splitlines() if proc.stdout is not None else None
        )
        if parsed_resp is None or len(parsed_resp) != 1:
            raise ValueError("Error finding Go version")
        else:
            go_version_text = parsed_resp[0].decode("utf-8")
            go_version = re.findall(r"\d\.\d+", go_version_text)
            if [int(x) for x in go_version[0].split(".")] >= [1, 17]:
                return True
            return False
    except Exception as e:
        print(e)
        return False


def is_in_range(value, min, max) -> bool:
    """Checks if a value is in the range of two others inclusive

    Args:
        value (Any): Value to check whether it is in range
        min (Any): Lower inclusive bound of the range check
        max (Any): Upper inclusive bound of the range check"""
    if value >= min and value <= max:
        return True
    return False


def transform_csv_to_json(sample_csv: pd.DataFrame) -> dict[str, dict[int, Area]]:
    """From Adi. Used to transform a nav file CSV to JSON.

    Args:
        sample_csv (pd.DataFrame): Dataframe containing information about areas of each map

    Returns:
        dict[str, dict[int, Area]] containing information about each area of each map"""
    final_dic: dict[str, dict[int, Area]] = {}
    for cur_map in sample_csv["mapName"].unique():
        map_dic: dict[int, Area] = {}
        for i in sample_csv[sample_csv["mapName"] == cur_map].index:
            cur_tile = sample_csv.iloc[i]
            # Would rather initiate this as an empty 'Area' typeddict
            cur_dic = {}
            # And cast cur_feature to Literal["mapName","areaId","areaName","northWestX",...]
            # However casting from Any to Literal does not work in mypy
            for cur_feature in sample_csv.columns:
                if cur_feature not in ["mapName", "areaId"]:
                    cur_dic[cur_feature] = cur_tile[cur_feature]
            map_dic[cur_tile["areaId"]] = cur_dic  # type: ignore[assignment]
        final_dic[cur_map] = map_dic
    return final_dic
