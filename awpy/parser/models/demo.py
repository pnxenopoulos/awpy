"""Defines the Demo class, which stores a demo's parsed data."""

import pandas as pd
from pydantic import BaseModel

from awpy.parser import models


class Demo(BaseModel):
    """Class to store a demo's data."""

    header: models.DemoHeader
    rounds: pd.DataFrame
    kills: pd.DataFrame
    damages: pd.DataFrame
    grenades: pd.DataFrame
    effects: pd.DataFrame
    flashes: pd.DataFrame
    weapon_fires: pd.DataFrame
    bomb_events: pd.DataFrame
    ticks: pd.DataFrame
