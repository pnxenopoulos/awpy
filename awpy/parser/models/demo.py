"""Defines the Demo class, which stores a demo's parsed data."""

from typing import TypedDict

import pandas as pd

from awpy.parser.models.header import DemoHeader


class Demo(TypedDict):
    """Class to store a demo's data."""

    header: DemoHeader
    rounds: pd.DataFrame
    kills: pd.DataFrame
    damages: pd.DataFrame
    grenades: pd.DataFrame
    # flashes: pd.DataFrame
    effects: pd.DataFrame
    bomb_events: pd.DataFrame
    ticks: pd.DataFrame
