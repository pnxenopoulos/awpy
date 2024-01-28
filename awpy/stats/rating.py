"""Methodology to replicate HLTV Rating 2.0"""

import pandas as pd

from awpy.parser.models.demo import Demo

# from awpy.stats.adr import adr
# from awpy.stats.kast import kast


def impact(demo: Demo) -> pd.DataFrame:
    """Calculates the impact rating for each player in the demo.

    Args:
        demo (Demo): The demo to calculate the impact rating for.

    Returns:
        pd.DataFrame: DataFrame with the impact rating for each player
            in the demo, tabulated by side.
    """
    # kills_per_round = 0
    # assists_per_round = 0
    # deaths_per_round = 0
    # adr = adr(demo)
    # kast = kast(demo)
    raise NotImplementedError
