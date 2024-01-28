"""Defines the Demo class, which stores a demo's parsed data."""

import pandas as pd
from pydantic import BaseModel, ConfigDict, validator

from .header import DemoHeader


class Demo(BaseModel):
    """Class to store a demo's data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: DemoHeader
    rounds: pd.DataFrame
    kills: pd.DataFrame
    damages: pd.DataFrame
    grenades: pd.DataFrame
    effects: pd.DataFrame
    flashes: pd.DataFrame
    weapon_fires: pd.DataFrame
    bomb_events: pd.DataFrame
    ticks: pd.DataFrame

    @validator(
        "rounds",
        "kills",
        "damages",
        "grenades",
        "effects",
        "flashes",
        "weapon_fires",
        "bomb_events",
        "ticks",
        pre=True,
    )
    def validate_dataframe(self, v: pd.DataFrame):
        """Validate that the field is a pandas DataFrame."""
        if not isinstance(v, pd.DataFrame):
            raise ValueError("Field must be a pandas DataFrame")
        return v
