"""Methodology to calculate Kill, Assist, Survival, and Trade (KAST) %."""

import pandas as pd

from awpy.parser.models.demo import Demo


def kast(_demo: Demo) -> pd.DataFrame:
    """Calculates the KAST % for each player in the demo.

    Args:
        demo (Demo): The demo to calculate the KAST % for.

    Returns:
        pd.DataFrame: DataFrame with the KAST% for each player in
            the demo, tabulated by side.
    """
    raise NotImplementedError
