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


def check_go_version():
    """ Function to check the Golang version of the current machine, returns True if greater than 1.14.0
    """
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
