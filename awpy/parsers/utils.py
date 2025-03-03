"""Module for parsing utils."""

import polars as pl


def get_event_from_parsed_events(
    events: dict[str, pl.DataFrame], key: str, *, empty_if_not_found: bool = False
) -> pl.DataFrame:
    """Retrieve a required event DataFrame from the events dictionary.

    Args:
        events: Dictionary of event DataFrames.
        key: The key for the required event.
        empty_if_not_found: If True, return an empty DataFrame if the event is not found.

    Returns:
        The corresponding polars DataFrame for the event.

    Raises:
        KeyError: If the event key is missing or its value is None.
    """
    event_df = events.get(key)
    if event_df is None:
        if empty_if_not_found:
            return pl.DataFrame()
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


def get_columns_with_prefix(df: pl.DataFrame, prefix: str) -> list[str]:
    """Return a list of column names in the DataFrame that start with the given prefix.

    Parameters:
        df (pl.DataFrame): The input DataFrame.
        prefix (str): The prefix to filter column names.

    Returns:
        list[str]: A list of column names that start with the prefix.
    """
    return [col for col in df.columns if col.startswith(prefix)]


def rename_columns_with_affix(
    df: pl.DataFrame,
    old_affix: str,
    new_affix: str,
    *,
    is_prefix: bool = True,
) -> pl.DataFrame:
    """Rename columns by replacing old_affix with new_affix for a Polars DataFrame.

    If is_prefix is True, the function replaces a prefix; otherwise, it replaces a suffix.

    Args:
        df (pl.DataFrame): DataFrame whose columns are to be renamed.
        old_affix (str): Old affix to be replaced.
        new_affix (str): New affix to replace the old one.
        is_prefix (bool, optional): If True, perform prefix replacement, else suffix. Defaults to True.

    Returns:
        pl.DataFrame: DataFrame with renamed columns.
    """
    new_columns = {}
    for col in df.columns:
        if is_prefix and col.startswith(old_affix):
            new_columns[col] = new_affix + col[len(old_affix) :]
        elif not is_prefix and col.endswith(old_affix):
            new_columns[col] = col[: -len(old_affix)] + new_affix
    return df.rename(new_columns)


def fix_common_names(df: pl.DataFrame) -> pl.DataFrame:
    """Fixes common column name values and data types.

    Args:
        df (pl.DataFrame): DataFrame to fix.

    Returns:
        pl.DataFrame: DataFrame with fixed column names and data types.
    """
    # last_place_name -> place
    renamed_df = rename_columns_with_affix(df, old_affix="last_place_name", new_affix="place", is_prefix=False)

    # steamid to u64
    for col in renamed_df.columns:
        if col.endswith("steamid"):
            renamed_df = renamed_df.with_columns(pl.col(col).cast(pl.UInt64))

    # CT -> ct, TERRORIST -> t
    for col in renamed_df.columns:
        if col.endswith("team_name"):
            renamed_df = renamed_df.with_columns(
                pl.col(col).map_elements(lambda x: {"CT": "ct", "TERRORIST": "t"}.get(x, x), return_dtype=pl.String)
            )

    # team_name -> side
    renamed_df = rename_columns_with_affix(renamed_df, old_affix="team_name", new_affix="side", is_prefix=False)

    # armor_value -> armor
    return rename_columns_with_affix(renamed_df, old_affix="armor_value", new_affix="armor", is_prefix=False)
