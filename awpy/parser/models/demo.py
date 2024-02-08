"""Defines the Demo class, which stores a demo's parsed data."""

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

from .header import DemoHeader


class Demo(BaseModel):
    """Class to store a demo's data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: DemoHeader
    events: dict[str, pd.DataFrame]
    ticks: pd.DataFrame | None
    grenades: pd.DataFrame | None

    @field_validator("events")
    @classmethod
    def validate_round_events(cls, events: dict[str, pd.DataFrame]):
        """Validate that the events DataFrame contains the necessary events."""
        if "round_start" not in events:
            raise ValueError("No round_start events found")
        if "round_freeze_end" not in events:
            raise ValueError("No round_freeze_end events found")
        if "round_end" not in events:
            raise ValueError("No round_end events found")
        if "round_officially_ended" not in events:
            raise ValueError("No round_officially_ended events found")
        return events

    @field_validator("events")
    @classmethod
    def add_event_name_to_dataframe(cls, events: dict[str, pd.DataFrame]):
        """Apply the event name to the DataFrame."""
        for event_name, df in events.items():
            df["event_type"] = event_name
        return events
