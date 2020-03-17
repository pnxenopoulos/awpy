""" Data cleaning functions
"""

import pandas as pd

from csgo.analytics.distance import point_distance


def clean_footsteps(df, max_dist = 500):
    """ A function to clean a dataframe of footsteps, as created by the match_parser
    """
    for r in range(0, df.RoundNum.max()+1):
        for p in df.SteamID.unique():
            player_df = df[(df["RoundNum"] == r) & (df["SteamID"] == p)]
            player_pos = []
            player_pos_clean = []
            for i, row in player_df.iterrows():
                player_pos.append((row["X"], row["Y"], row["Z"]))
            for i, pos in enumerate(player_pos):
                if i == 0:
                    player_pos_clean.append(0)
                else:
                    player_pos_clean.append(distance.euclidean(list(pos), list(player_pos[i-1])))
    return NotImplementedError