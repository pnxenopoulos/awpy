"""Methodology to calculate Average Damage per Round (ADR)."""

import pandas as pd

from awpy.parser.models.demo import Demo


def adr(_demo: Demo) -> pd.DataFrame:
    """Calculate the Average Damage per Round (ADR) for each player.

    Args:
        demo (Demo): The demo to calculate the ADR for.

    Returns:
        pd.DataFrame: DataFrame with the ADR for each player in
            the demo, tabulated by side.
    """
    raise NotImplementedError
