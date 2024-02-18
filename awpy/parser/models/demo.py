"""Defines the Demo class, which stores a demo's parsed data."""

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

from awpy.parser.models.header import DemoHeader


class Demo(BaseModel):
    """Class to store a demo's data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    header: DemoHeader
    events: dict[str, pd.DataFrame]
    ticks: pd.DataFrame | None
    grenades: pd.DataFrame | None

    @field_validator("events")
    @classmethod
    def validate_round_events(
        cls: type["Demo"], events: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        """Validate that the events DataFrame contains the necessary events."""
        if "round_start" not in events:
            no_round_start_msg = "No round_start events found"
            raise ValueError(no_round_start_msg)
        if "round_freeze_end" not in events:
            no_round_freeze_msg = "No round_freeze_end events found"
            raise ValueError(no_round_freeze_msg)
        if "round_end" not in events:
            no_round_end_msg = "No round_end events found"
            raise ValueError(no_round_end_msg)
        if "round_officially_ended" not in events:
            no_round_officially_ended_msg = "No round_officially_ended events found"
            raise ValueError(no_round_officially_ended_msg)
        if "bomb_planted" not in events:
            no_bomb_planted_msg = "No bomb_planted events found"
            raise ValueError(no_bomb_planted_msg)
        return events

    @field_validator("events")
    @classmethod
    def add_event_name_to_dataframe(
        cls: type["Demo"], events: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        """Apply the event name to the DataFrame."""
        for event_name, df in events.items():
            df["event_type"] = event_name
        return events
