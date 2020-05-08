""" Util functions for csgo package
"""

import json
import numpy as np


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
