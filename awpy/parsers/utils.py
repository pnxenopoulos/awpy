"""Module for parsing utils."""

import polars as pl


def get_event_from_parsed_events(events: dict[str, pl.DataFrame], key: str) -> pl.DataFrame:
    """Retrieve a required event DataFrame from the events dictionary.

    Args:
        events: Dictionary of event DataFrames.
        key: The key for the required event.

    Returns:
        The corresponding polars DataFrame for the event.

    Raises:
        KeyError: If the event key is missing or its value is None.
    """
    event_df = events.get(key)
    if event_df is None:
        missing_key_err_msg = f"Required event '{key}' is missing from the events dictionary."
        raise KeyError(missing_key_err_msg)
    return event_df


def validate_required_columns(df: pl.DataFrame, required_columns: set[str], df_name: str = "DataFrame") -> None:
    """Validate that the given DataFrame contains all required columns.

    Parameters:
        df (pl.DataFrame): The DataFrame to validate.
        required_columns (set[str]): A set of column names that must be present
            in the DataFrame.
        df_name (str, optional): Name of the DataFrame for error messaging.
            Defaults to "DataFrame".

    Raises:
        KeyError: If one or more required columns are missing.
    """
    missing = required_columns - set(df.columns)
    if missing:
        missing_col_err_msg = f"{df_name} is missing required columns: {missing}"
        raise KeyError(missing_col_err_msg)


def rename_col_prefix(df: pl.DataFrame, prefix: str = "prefix_", new_prefix: str = "new_") -> pl.DataFrame:
    """Rename all columns in the DataFrame that start with a prefix to use a new one.

    For example, if a column is named "prefix_column1" and the prefix is "prefix_" while
    the new_prefix is "postfix_", the column will be renamed to "postfix_column1".
    Columns that do not start with the specified prefix remain unchanged.

    Parameters:
        df (pl.DataFrame): The DataFrame whose columns should be renamed.
        prefix (str, optional): The prefix to search for in column names.
            Defaults to "prefix_".
        new_prefix (str, optional): The new prefix to replace the old prefix.
            Defaults to "new_".

    Returns:
        pl.DataFrame: A new DataFrame with columns renamed accordingly.
    """
    rename_dict = {col: new_prefix + col[len(prefix) :] for col in df.columns if col.startswith(prefix)}
    return df.rename(rename_dict)


def get_columns_with_prefix(df: pl.DataFrame, prefix: str) -> list[str]:
    """Return a list of column names in the DataFrame that start with the given prefix.

    Parameters:
        df (pl.DataFrame): The input DataFrame.
        prefix (str): The prefix to filter column names.

    Returns:
        list[str]: A list of column names that start with the prefix.
    """
    return [col for col in df.columns if col.startswith(prefix)]
