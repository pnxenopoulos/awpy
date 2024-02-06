"""Methodology to replicate HLTV Rating 2.0."""

import pandas as pd

from awpy.parser.models.demo import Demo


def impact(_demo: Demo) -> pd.DataFrame:
    """Calculates the impact rating for each player in the demo.

    Args:
        demo (Demo): The demo to calculate the impact rating for.

    Returns:
        pd.DataFrame: DataFrame with the impact rating for each player
            in the demo, tabulated by side.
    """
    raise NotImplementedError


def rating(_demo: Demo) -> pd.DataFrame:
    """Calculates the HLTV Rating 2.0 for each player in the demo.

    Args:
        demo (Demo): The demo to calculate the rating for.

    Returns:
        pd.DataFrame: DataFrame with the HLTV Rating 2.0 for each player
            in the demo, tabulated by side.
    """
    raise NotImplementedError
