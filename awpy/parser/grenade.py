"""Parsing methods for projectiles (grenades)."""
import pandas as pd
import warnings


def parse_smokes_and_infernos(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the smokes and infernos of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with start/stops
            for infernos and smokes.

    Returns:
        pd.DataFrame: DataFrame with the parsed smokes and infernos data.
    """
    if not parsed:
        warnings.warn("No smoke/inferno events found in the demofile.", stacklevel=2)
        return pd.DataFrame(columns=["entityid", "tick", "x", "y", "z", "event"])

    all_event_dfs = [
        df.assign(event=key).loc[:, ["entityid", "tick", "x", "y", "z", "event"]]
        for key, df in parsed
        if not df.empty
    ]

    return pd.concat(all_event_dfs).sort_values(by=["tick", "entityid"])


def parse_blinds(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the blinds of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with blind events.

    Returns:
        pd.DataFrame: DataFrame with the parsed blind events data.
    """
    if not parsed:
        warnings.warn("No player blind events found in the demofile.", stacklevel=2)
        return pd.DataFrame(
            columns=[
                "flasher",
                "flasher_steamid",
                "blind_duration",
                "entityid",
                "tick",
                "victim",
                "victim_steamid",
            ]
        )

    # Assuming the first element of 'parsed' always contains the relevant DataFrame
    blind_df = parsed[0][1]

    # Renaming columns
    rename_columns = {
        "attacker_name": "flasher",
        "attacker_steamid": "flasher_steamid",
        "user_name": "victim",
        "user_steamid": "victim_steamid",
    }
    blind_df = blind_df.rename(columns=rename_columns)

    # Converting data types
    for col in ["flasher_steamid", "victim_steamid"]:
        blind_df[col] = blind_df[col].astype("Int64")

    return blind_df.sort_values(by="tick")
