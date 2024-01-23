"""Methods for parsing weapon-related entities and events."""
import pandas as pd
import warnings


def parse_weapon_fires(parsed: list[tuple]) -> pd.DataFrame:
    """Parse the weapon fires of the demofile.

    Args:
        parsed (list[tuple]): List of tuples containing DataFrames with weaponfire events.

    Returns:
        pd.DataFrame: DataFrame with the parsed weapon fire events data.
    """
    if not parsed:
        warnings.warn("No weapon fires found in the demofile.", stacklevel=2)
        return pd.DataFrame(columns=["silenced", "tick", "player", "steamid", "weapon"])

    # Assuming the first element of 'parsed' always contains the relevant DataFrame
    weapon_fires_df = parsed[0][1]

    # Renaming columns
    rename_columns = {
        "user_name": "player",
        "user_steamid": "steamid",
    }
    weapon_fires_df = weapon_fires_df.rename(columns=rename_columns)

    # Converting data types
    weapon_fires_df["steamid"] = weapon_fires_df["steamid"].astype("Int64")

    return weapon_fires_df.sort_values(by="tick")
