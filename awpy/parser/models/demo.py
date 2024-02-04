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
    @classmethod
    def validate_dataframe(cls, val: pd.DataFrame) -> bool:  # noqa: ANN102
        """Validate that the field is a pandas DataFrame.

        Args:
            val (pd.DataFrame): A dataframe value to validate.

        Returns:
            bool: True if the fields are pandas DataFrames.
        """
        if not isinstance(val, pd.DataFrame):
            type_error_msg = f"{val} must be a pandas DataFrame"
            raise TypeError(type_error_msg)
        return val
