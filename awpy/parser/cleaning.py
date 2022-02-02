""" Data cleaning functions
"""

import difflib
import numpy as np
import pandas as pd
import textdistance


def associate_entities(game_names=[], entity_names=[], metric="lcss"):
    """A function to return a dict of associated entities. Accepts

    Args:
        game_names (list): A list of names generated by the demofile
        entity_names (list): A list of names
        metric (string): A string indicating distance metric, one of lcss, hamming, levenshtein, jaro, difflib

    Returns:
        A dictionary where the keys are entries in game_names, values are the matched entity names.
    """
    if metric.lower() == "lcss":
        dist_metric = textdistance.lcsseq.distance
    elif metric.lower() == "hamming":
        dist_metric = textdistance.hamming.distance
    elif metric.lower() == "levenshtein":
        dist_metric = textdistance.levenshtein.distance
    elif metric.lower() == "jaro":
        dist_metric = textdistance.jaro.distance
    elif metric.lower() == "difflib":
        entities = {}
        for gn in game_names:
            if gn is not None and gn is not np.nan:
                closest_name = difflib.get_close_matches(
                    gn, entity_names, n=1, cutoff=0.0
                )
                if len(closest_name) > 0:
                    entities[gn] = closest_name[0]
                else:
                    entities[gn] = None
        entities[None] = None
        return entities
    else:
        raise ValueError(
            "Metric can only be lcss, hamming, levenshtein, jaro or difflib"
        )
    entities = {}
    for gn in game_names:
        if gn is not None and gn is not np.nan and gn != "":
            name_distances = []
            names = []
            if len(entity_names) > 0:
                for p in entity_names:
                    name_distances.append(dist_metric(gn.lower(), p.lower()))
                    names.append(p)
                entities[gn] = names[np.argmin(name_distances)]
                popped_name = entity_names.pop(np.argmin(name_distances))
        if gn == "":
            entities[gn] = None
    entities[None] = None
    return entities


def replace_entities(df, col_name, entity_dict):
    """A function to replace values in a Pandas df column given an entity dict, as created in associate_entities()

    Args:
        df (DataFrame)     : A Pandas DataFrame
        col_name (string)  : A column in the Pandas DataFrame
        entity_dict (dict) : A dictionary as created in the associate_entities() function

    Returns:
        A dataframe with replaced names.
    """
    if col_name not in df.columns:
        raise ValueError("Column does not exist!")
    df[col_name].replace(entity_dict, inplace=True)
    return df