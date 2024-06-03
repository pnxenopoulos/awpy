"""Calculates Average Damage Per Round."""

import pandas as pd

from awpy import Demo
from awpy.stats.utils import get_player_rounds


def adr(
    demo: Demo,
    team_dmg: bool = False,  # noqa: FBT001, FBT002
    self_kills: bool = True,  # noqa: FBT001, FBT002
) -> pd.DataFrame:
    """Calculates Average Damage Per Round. Does not include team damage.

    Args:
        demo (Demo): A parsed Awpy demo.
        team_dmg (bool, optional): Whether to use team damage. Defaults to False.
        self_kills (bool, optional): Whether to use self kills. Defaults to True.

    Returns:
        pd.DataFrame: A dataframe of the player info + adr.

    Raises:
        ValueError: If damages are missing in the parsed demo.
    """
    if demo.damages is None:
        missing_damages_error_msg = "Damages is missing in the parsed demo!"
        raise ValueError(missing_damages_error_msg)

    damages = demo.damages

    # Remove team damage
    if team_dmg:
        damages = damages[damages["attacker_side"] != damages["victim_side"]]

    # Remove self kills
    if self_kills:
        damages = damages[~damages["attacker_name"].isna()]

    # Calculate all/ct/t total damage
    damages_all = (
        damages.groupby(["attacker_name", "attacker_steamid"])
        .dmg_health_real.sum()
        .reset_index(name="dmg")
    )
    damages_all["side"] = "all"
    damages_ct = (
        damages[damages["attacker_side"] == "CT"]
        .groupby(["attacker_name", "attacker_steamid"])
        .dmg_health_real.sum()
        .reset_index(name="dmg")
    )
    damages_ct["side"] = "CT"
    damages_t = (
        damages[damages["attacker_side"] == "TERRORIST"]
        .groupby(["attacker_name", "attacker_steamid"])
        .dmg_health_real.sum()
        .reset_index(name="dmg")
    )
    damages_t["side"] = "TERRORIST"
    damage_agg = pd.concat([damages_all, damages_ct, damages_t])
    damage_agg.columns = ["name", "steamid", "dmg", "side"]

    # Get rounds played by each player/side
    player_rounds_agg = get_player_rounds(demo)

    # Merge damage and rounds
    adr_df = damage_agg.merge(player_rounds_agg, on=["name", "steamid", "side"])
    adr_df["adr"] = adr_df["dmg"] / adr_df["n_rounds"]

    return adr_df[["name", "steamid", "side", "n_rounds", "dmg", "adr"]]
