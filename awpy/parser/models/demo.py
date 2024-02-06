"""Defines the Demo class, which stores a demo's parsed data."""

import pandas as pd
from pydantic import BaseModel, ConfigDict

from .header import DemoHeader


class Demo(BaseModel):
    """Class to store a demo's data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: DemoHeader
    events: dict[str, pd.DataFrame]
    ticks: pd.DataFrame | None
    grenades: pd.DataFrame
