""" Util functions for csgo package
"""

import json
import numpy as np
import re
import subprocess


class AutoVivification(dict):
    """Implementation of perl's autovivification feature. Stolen from https://stackoverflow.com/questions/651794/whats-the-best-way-to-initialize-a-dict-of-dicts-in-python"""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


def check_go_version():
    """Function to check the Golang version of the current machine, returns True if greater than 1.14.0"""
    try:
        proc = subprocess.Popen(["go", "version"], stdout=subprocess.PIPE)
        parsed_resp = proc.stdout.read().splitlines()
        if len(parsed_resp) != 1:
            raise ValueError("Error finding Go version")
        else:
            go_version_text = parsed_resp[0].decode("utf-8")
            go_version = re.findall(r"\d\.\d+", go_version_text)
            if int(go_version[0].replace(".", "")) >= 117:
                return True
            else:
                return False
    except Exception as e:
        print(e)
        return False


def is_in_range(value, min, max):
    if value >= min and value <= max:
        return True
    else:
        return False


def transform_csv_to_json(sampleCsv):
    """From Adi. Used to transform a nav file CSV to JSON."""
    finalDic = {}
    for curMap in sampleCsv["mapName"].unique():
        mapDic = {}
        for i in sampleCsv[sampleCsv["mapName"] == curMap].index:
            curTile = sampleCsv.iloc[i]
            curDic = {}
            for curFeature in sampleCsv.columns:
                if curFeature not in ["mapName", "areaId"]:
                    curDic[curFeature] = curTile[curFeature]
            mapDic[curTile["areaId"]] = curDic
        finalDic[curMap] = mapDic
    return finalDic
