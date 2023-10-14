"""This module defines the DemoParser class that handles the core parsing functionality.

Core functionality is parsing and cleaning a Counter Strike demo file.

Example::

    from awpy.parser import DemoParser

    # Create parser object
    # Set log=True above if you want to produce a logfile for the parser
    demo_parser = DemoParser(
        demofile = "og-vs-natus-vincere-m1-dust2.dem",
        demo_id = "OG-NaVi-BLAST2020",
        trade_time=5,
        buy_style="hltv"
    )

    # Parse the demofile, output results to dictionary
    data = demo_parser.parse()

https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb
"""

import pandas as pd

from demoparser2 import DemoParser
from awpy.parser.models import Demo, DemoHeader
from awpy.parser.enums import GameEvent

def parse_demo(file: str) -> Demo:
    parser = DemoParser(file)

    # Header
    parsed_header = parser.parse_header()
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
    header = DemoHeader(**parsed_header)

    # Rounds
    event_order = {
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.BUYTIME_ENDED.value: 3,
        GameEvent.ROUND_END.value: 4,
    }
    parsed_round_times = parser.parse_events([
        GameEvent.ROUND_START.value,
        GameEvent.ROUND_FREEZE_END.value,
        GameEvent.BUYTIME_ENDED.value,
        GameEvent.ROUND_END.value,
        GameEvent.ROUND_OFFICIALLY_ENDED.value
    ])
    round_events = []
    for _, round_event in enumerate(parsed_round_times):
        round_event[1]["event"] = round_event[0]
        round_events.append(round_event[1].loc[:,["tick", "event"]])
    rounds_df = pd.concat(round_events)
    rounds_df['order'] = rounds_df['event'].map(event_order)
    rounds_df = rounds_df.sort_values(by="tick")

    grenades = parser.parse_grenades()
    return None