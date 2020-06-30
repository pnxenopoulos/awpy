""" Util functions for csgo package
"""

import json
import numpy as np
import re
import subprocess


class NpEncoder(json.JSONEncoder):
    """ Class to change numpy encodings for JSON file writing
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)


class AutoVivification(dict):
    """ Implementation of perl's autovivification feature. Stolen from https://stackoverflow.com/questions/651794/whats-the-best-way-to-initialize-a-dict-of-dicts-in-python
    """

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


def check_go_version():
    """ Function to check the Golang version of the current machine, returns True if greater than 1.14.0
    """
    try:
        proc = subprocess.Popen(["go", "version"], stdout=subprocess.PIPE)
        parsed_resp = proc.stdout.read().splitlines()
        if len(parsed_resp) != 1:
            raise ValueError("Error finding Go version")
        else:
            go_version_text = parsed_resp[0].decode("utf-8")
            go_version = re.findall(r"\d\.\d+\.\d", go_version_text)
            if int(go_version[0].replace(".", "")) >= 1140:
                return True
            else:
                return False
    except Exception as e:
        print(e)
        return False
