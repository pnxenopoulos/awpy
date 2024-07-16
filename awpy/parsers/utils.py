"""Module for parsing utils."""

import pandas as pd


def parse_col_types(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the column types of a dataframe.

    Args:
        df: A pandas DataFrame.

    Returns:
        A DataFrame with the column types.
    """
    for col in df.columns:
        # SteamIDs should be ints
        if "steamid" in col:
            df[col] = df[col].astype(str)
    return df
