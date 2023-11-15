import pandas as pd
from awpy.parser.models.demo import Demo

def adr(demo: Demo) -> pd.DataFrame:
    rounds_df = demo["rounds"]
    tick_df = demo["ticks"]

    # Get viable ticks
    inplay_ticks = tick_df[["tick", "game_phase"]]
    inplay_ticks = inplay_ticks[inplay_ticks["game_phase"].isin(["startgame", "preround", "teamwin", "restart"])]
    inplay_ticks = inplay_ticks.drop_duplicates()

    player_ticks = tick_df[["tick", "steamid", "side", "health"]]
    player_ticks = player_ticks[player_ticks["side"].isin(["t", "ct"])]
    player_ticks_shifted = player_ticks.copy()
    player_ticks_shifted["tick"] = player_ticks_shifted["tick"] + 1

    damage_df = demo["damages"]
    damage_df = damage_df.merge(inplay_ticks, on = "tick", how="inner")

    damage_df = damage_df.merge(player_ticks, left_on = ["attacker_steamid", "tick"], right_on = ["steamid", "tick"], how="left", suffixes=("", "_attacker"))
    damage_df = damage_df.merge(player_ticks_shifted, left_on = ["victim_steamid", "tick"], right_on = ["steamid", "tick"], how="left", suffixes=("", "_victim"))
    
    damage_df_team_dmg_removed = damage_df[damage_df["side"] != damage_df["side_victim"]]
    damage_df_team_dmg_removed["dmg_health_adj"] = damage_df_team_dmg_removed.apply(lambda x: min(x["dmg_health"], x["health_victim"]), axis=1)
    return None