import pandas as pd

def agg_damages(damage_data: pd.DataFrame) -> pd.DataFrame:
    """Returns a dataframe with aggregated damage events."""
    cols_to_groupby = list(damage_data.columns[0:25])
    cols_to_groupby.extend(list(damage_data.columns[29:]))
    damage_data = damage_data.groupby(cols_to_groupby).sum().reset_index()
    return damage_data