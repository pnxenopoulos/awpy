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
import numpy as np

from demoparser2 import DemoParser
from awpy.parser.models import Demo, DemoHeader
from awpy.parser.enums import GameEvent

def parse_header(parsed_header: dict) -> DemoHeader:
    """Parse the header of the demofile.

    Args:
        parsed_header (dict): The header of the demofile.

    Returns:
        DemoHeader: The parsed header of the demofile.
    """
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
    header = DemoHeader(**parsed_header)
    return header

def parse_rounds(parsed_round_events: list[tuple]) -> pd.DataFrame:
    """Parse the rounds of the demofile.
    Args:
        parsed_round_events (list[tuple]): Output of parser.parse_events(...)
    Returns:
        pd.DataFrame: Pandas DataFrame with the parsed rounds data.
    """
    # Get the round events in dataframe order
    round_events = []
    for _, round_event in enumerate(parsed_round_events):
        round_event[1]["event"] = round_event[0]
        round_events.append(round_event[1].loc[:,["tick", "event"]])
    round_event_df = pd.concat(round_events)
    # Ascribe order to event types and sort by tick and order
    event_order = {
        GameEvent.ROUND_OFFICIALLY_ENDED.value: 0,
        GameEvent.ROUND_START.value: 1,
        GameEvent.ROUND_FREEZE_END.value: 2,
        GameEvent.BUYTIME_ENDED.value: 3,
        GameEvent.ROUND_END.value: 4,
    }
    round_event_df['order'] = round_event_df['event'].map(event_order)
    round_event_df = round_event_df.sort_values(by=["tick", "order"])
    parsed_rounds_df = create_round_df(round_event_df)
    return parsed_rounds_df

def create_round_df(round_event_df: pd.DataFrame) -> pd.DataFrame:
    """_summary_
    Args:
        round_event_df (pd.DataFrame): _description_
    Returns:
        pd.DataFrame: _description_
    """
    # Initialize empty lists for each event type
    round_start = []
    freeze_time_end = []
    buy_time_end = []
    round_end = []
    round_end_official = []
    current_round = None
    # Iterate through the DataFrame and populate the lists
    for _, row in round_event_df.iterrows():
        if row['event'] == 'round_start':
            if current_round is not None:
                # Append the collected events to the respective lists
                round_start.append(current_round.get('round_start', None))
                freeze_time_end.append(current_round.get('freeze_time_end', None))
                buy_time_end.append(current_round.get('buy_time_end', None))
                round_end.append(current_round.get('round_end', None))
                round_end_official.append(current_round.get('round_end_official', None))
            # Start a new round
            current_round = {'round_start': row['tick']}
        elif current_round is not None:
            if row['event'] == 'round_freeze_end':
                current_round['freeze_time_end'] = row['tick']
            elif row['event'] == 'buytime_ended':
                current_round['buy_time_end'] = row['tick']
            elif row['event'] == 'round_end':
                current_round['round_end'] = row['tick']
            elif row['event'] == 'round_officially_ended':
                current_round['round_end_official'] = row['tick']
    # Append the last collected round's events
    round_start.append(current_round.get('round_start', None))
    freeze_time_end.append(current_round.get('freeze_time_end', None))
    buy_time_end.append(current_round.get('buy_time_end', None))
    round_end.append(current_round.get('round_end', None))
    round_end_official.append(current_round.get('round_end_official', None))
    # Create a new DataFrame with the desired columns
    parsed_rounds_df = pd.DataFrame({
        'round_start': round_start,
        'freeze_time_end': freeze_time_end,
        'buy_time_end': buy_time_end,
        'round_end': round_end,
        'round_end_official': round_end_official
    })
    parsed_rounds_df = parsed_rounds_df.fillna(-1)
    parsed_rounds_df = parsed_rounds_df.astype(int)
    return parsed_rounds_df


def parse_demo(file: str) -> Demo:
    parser = DemoParser(file)

    # Header
    parsed_header = parser.parse_header()
    header = parse_header(parsed_header)

    # Rounds
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
    rounds_df = rounds_df.sort_values(by=["tick", "order"])

    grenades = parser.parse_grenades()
    return None