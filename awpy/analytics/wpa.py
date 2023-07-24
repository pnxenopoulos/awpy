"""Will provide functionality for WPA and win probabilities.

WPA stands for Win Probability Added and is described in this paper:
https://arxiv.org/pdf/2011.01324.pdf.
"""
from typing import Any
import ast
import requests
from awpy.types import GameFrame

SIMPLE_WP_MODEL = None
ADV_WP_MODEL = None
URL = "https://www.hltv.org/scripts/hltv.js"
SAVE_PATH = "hltv.js"



def state_win_probability(frame: GameFrame, model: Any) -> dict:  # noqa: ANN401
    """Predicts the win probability of a given frame.

    Args:
        frame (dict): Dict output of a frame generated from the DemoParser class
        model (Unknown): Model to predict win probabability from.

    Returns:
        A dictionary containing the CT and T round win probabilities
    """
    raise NotImplementedError


def round_win_probability(ct_score: int, t_score: int, map_name: str) -> dict:
    """Estimates of game win probability using information from the HLTV win matrix.

    Args:
        ct_score (int): CT Score
        t_score (int): T Score
        map_name (str): Map the demo is from

    Returns:
        A dictionary containing the CT game win, T game win and Draw probabilities
    """
    raise NotImplementedError


def _get_matrix_data(url, save_path):
    """Helper to get the latest data.
    
    """
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                 "AppleWebKit/537.36 (KHTML, like Gecko) " \
                 "Chrome/58.0.3029.110 Safari/537.3"
    headers = {"User-Agent": user_agent}

    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()

        with open(SAVE_PATH, 'wb') as f:
            f.write(response.content)

        print(f"File downloaded successfully and saved as '{SAVE_PATH}'.")

    except requests.RequestException as e:
        match e:
            case requests.exceptions.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
            case requests.exceptions.ConnectionError as conn_err:
                print(f"Connection error occurred: {conn_err}")
            case requests.exceptions.Timeout as timeout_err:
                print(f"Timeout error occurred: {timeout_err}")
            case requests.exceptions.RequestException as req_err:
                print(f"Other request error occurred: {req_err}")



def _clean_matrix_data(save_path):
    """Cleans the data from the JS object to a readable python dict 
        Finds the start and end index of n.winProbabilities, 
        replaces what we dont need, and adding double quotes.

    Returns:
        A dictionary containing the CT and T game winprobabilities
    

    """
    with open(save_path, encoding="utf-8") as f:
        js_code = f.read()

    start_index = js_code.find("n.winProbabilities")
    end_index = js_code.find("},{}],541:[function(e,t,n)")
    n_win_probabilities = js_code[start_index:end_index]

    cleaned_string = n_win_probabilities \
        .replace("n.winProbabilities=", "") \
        .replace("CT", "\'CT\'") \
        .replace("TERRORIST", "\'TERRORIST\'")
        
    winprobabilities = ast.literal_eval(cleaned_string)

    return winprobabilities


def _get_mapname(map_id):
    """Helper to get the map_name from map_id

        Returns:
            A str with the map_name
        
        """
    map_dict = {
                29: "de_cache", \
                32: "de_mirage", \
                33: "de_inferno", \
                34: "de_nuke", \
                35: "de_train", \
                39: "de_cbble", \
                40: "de_overpass", \
                46: "de_vertigo", \
                47: "de_ancient", \
                48: "de_anubis" }

    if map_id in map_dict:
        return map_dict[map_id]
    return None
