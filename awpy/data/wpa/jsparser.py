"""Module to fetch and clean WPA data from the HLTV website."""

import ast
import json

import requests

URL = "https://www.hltv.org/scripts/hltv.js"


def fetch_matrix_data() -> dict:
    """Function to get the latest matrix data from the HLTV.

    Returns:
        Saves the matrix to wpa.json
    """
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/58.0.3029.110 Safari/537.3"
    )
    headers = {"User-Agent": user_agent}

    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        resp = response.content.decode("utf-8")
        start_index = resp.find("n.winProbabilities")
        end_index = resp.find("},{}],541:[function(e,t,n)")
        js_code = resp[start_index:end_index]

        cleaned_string = (
            js_code.replace("n.winProbabilities=", "")
            .replace("CT", "'CT'")
            .replace("TERRORIST", "'TERRORIST'")
        )
        cleaned_dict = ast.literal_eval(cleaned_string)

        with open("wpa.json", "w", encoding="utf-8") as outfile:
            json.dump(cleaned_dict, outfile)
            print("File downloaded successfully and saved as wpa.json.")
            return cleaned_dict

    except requests.RequestException as err:
        match err:
            case requests.exceptions.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
            case requests.exceptions.ConnectionError as conn_err:
                print(f"Connection error occurred: {conn_err}")
            case requests.exceptions.Timeout as timeout_err:
                print(f"Timeout error occurred: {timeout_err}")
            case requests.exceptions.RequestException as req_err:
                print(f"Other request error occurred: {req_err}")
        return {}  # return an empty dict in case of error

if __name__ == "__main__":
    fetch_matrix_data()
