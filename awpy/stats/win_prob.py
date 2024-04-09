"""Calculates CT & T side likeliehood of winning a round at any given point"""

import pandas as pd
from typing import List, Dict, Union

from awpy import Demo


def win_probability(demo: Demo, ticks: Union[int, List[int]]) -> List[Dict[str, float]]:
    """
    Calculate win probabilities for specified ticks in a Counter-Strike match demo.

    Args:
        demo (Demo): A parsed demo object containing CS:GO match data.
        ticks (Union[int, List[int]]): A single tick or a list of ticks at which to calculate win probabilities.

    Returns:
        List[Dict[str, float]]: A list of dictionaries with the calculated win probabilities for CT and T sides for each tick.

    Raises:
        ValueError: If specified ticks are not found within the demo object or if ticks are from different rounds.
    """
    if not demo.ticks.empty:
        if isinstance(ticks, int):
            ticks = [ticks]
        
        # Gather round numbers for each specified tick
        round_numbers = []
        for tick in ticks:
            tick_data = demo.ticks[demo.ticks["tick"] == tick]
            if tick_data.empty:
                raise ValueError(f"No data found for tick {tick}.")
            round_numbers.append(tick_data["round"].iloc[0])
        
        # Check if all ticks belong to the same round
        if len(set(round_numbers)) > 1:
            raise ValueError("Specified ticks are from different rounds. Please ensure all ticks belong to the same round.")
            
        game_state = []

        # Process Game State/Feature Matrix
        for tick in ticks:
            tick_data = demo.ticks[demo.ticks["tick"] == tick]
            
            for round_number in tick_data["round"].unique():
                round_data = tick_data[tick_data["round"] == round_number]
                
                map_name = demo.header.map_name
                bomb_planted = round_data["is_bomb_planted"].iloc[0]
                players_alive_ct = round_data[(round_data["side"] == "CT") & (round_data["health"] > 0)]["steamid"].nunique()
                players_alive_t = round_data[(round_data["side"] == "TERRORIST") & (round_data["health"] > 0)]["steamid"].nunique()
                equipment_value_ct = round_data[(round_data["side"] == "CT") & (round_data["health"] > 0)]["current_equip_value"].sum()
                equipment_value_t = round_data[(round_data["side"] == "TERRORIST") & (round_data["health"] > 0)]["current_equip_value"].sum()
                hp_remaining_ct = round_data[(round_data["side"] == "CT") & (round_data["health"] > 0)]["health"].sum()
                hp_remaining_t = round_data[(round_data["side"] == "TERRORIST") & (round_data["health"] > 0)]["health"].sum()
                
                game_state.append({
                    "tick": tick,
                    "round": round_number,
                    "map_name": map_name,
                    "bomb_planted": bomb_planted,
                    "players_alive_ct": players_alive_ct,
                    "players_alive_t": players_alive_t,
                    "equipment_value_ct": equipment_value_ct,
                    "equipment_value_t": equipment_value_t,
                    "hp_remaining_ct": hp_remaining_ct,
                    "hp_remaining_t": hp_remaining_t,
                })
        
        return game_state
    else:
        raise ValueError("Ticks data is missing in the parsed demo.")


