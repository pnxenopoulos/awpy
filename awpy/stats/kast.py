"""Calculates the Kill, Assist, Survival, Trade %."""

import polars as pl

import awpy.constants
import awpy.demo


def calculate_trades(demo: awpy.demo.Demo, trade_length_in_seconds: float = 5.0) -> pl.DataFrame:
    """Calculates if kills are trades.

    A trade is a kill where the attacker of a player who recently died was
    killed shortly after the initial victim was killed.

    Args:
        demo (awpy.demo.Demo): A parsed Demo.
        trade_length_in_seconds (float, optional): Length of trade time in
                                                   seconds. Defaults to 5.0.

    Returns:
        pl.DataFrame: The input DataFrame with an additional boolean column `was_traded`
                      indicating whether the kill was traded.
    """
    # Calculate trade ticks
    trade_ticks = demo.tickrate * trade_length_in_seconds

    # Add a row index so we can later mark specific rows
    kills = demo.kills.with_row_index("row_idx")
    trade_indices = []

    # Get unique rounds as a list
    rounds = kills.select("round_num").unique().to_series().to_list()

    # For each round, iterate over kills in that round and check for trade conditions.
    for r in rounds:
        kills_round = kills.filter(pl.col("round_num") == r)
        # Convert the round's DataFrame to dictionaries for row-wise iteration.
        for row in kills_round.to_dicts():
            tick = row["tick"]
            victim_name = row["victim_name"]
            # Filter kills in the trade window for this round.
            kills_in_window = kills_round.filter((pl.col("tick") >= (tick - trade_ticks)) & (pl.col("tick") <= tick))
            # Get the list of attacker names in the window.
            attacker_names = kills_in_window.select("attacker_name").to_series().to_list()
            if victim_name in attacker_names:
                last_trade_row = None
                # Iterate over the window rows to get the last kill where the attacker equals the victim.
                for win_row in kills_in_window.to_dicts():
                    if win_row["attacker_name"] == victim_name:
                        last_trade_row = win_row["row_idx"]
                if last_trade_row is not None:
                    trade_indices.append(last_trade_row)

    # Mark rows whose row_idx is in our trade_indices list.
    trade_set = set(trade_indices)
    kills = kills.with_columns(pl.col("row_idx").is_in(list(trade_set)).alias("was_traded"))
    # Drop the temporary row index column.
    return kills.drop("row_idx")


def kast(demo: awpy.demo.Demo, trade_length_in_seconds: float = 3.0) -> pl.DataFrame:
    """Calculates Kill-Assist-Survival-Trade % (KAST) using Polars.

    Args:
        demo (awpy.demo.Demo): A parsed Awpy demo with kills and ticks as Polars DataFrames.
        trade_length_in_seconds (float, optional): Length of trade time in seconds. Defaults to 3.0.

    Returns:
        pl.DataFrame: A DataFrame of player info with KAST statistics. The returned DataFrame
                      contains the following columns:
                        - name: The player's name.
                        - steamid: The player's Steam ID.
                        - side: The team ("all", "ct", or "t").
                        - kast_rounds: Number of rounds contributing to KAST.
                        - n_rounds: Total rounds played.
                        - kast: The KAST percentage.

    Raises:
        ValueError: If kills or ticks are missing in the parsed demo.
    """
    # Mark trade kills
    kills_with_trades = calculate_trades(demo, trade_length_in_seconds)

    # --- Kills & Assists ---

    # Total kills
    kills_total = (
        kills_with_trades.select(["attacker_name", "attacker_steamid", "round_num"])
        .unique()
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_ct = (
        kills_with_trades.filter(pl.col("attacker_side") == awpy.constants.CT_SIDE)
        .select(["attacker_name", "attacker_steamid", "round_num"])
        .unique()
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )
    kills_t = (
        kills_with_trades.filter(pl.col("attacker_side") == awpy.constants.T_SIDE)
        .select(["attacker_name", "attacker_steamid", "round_num"])
        .unique()
        .rename({"attacker_name": "name", "attacker_steamid": "steamid"})
    )

    # Total assists
    assists_total = (
        kills_with_trades.select(["assister_name", "assister_steamid", "round_num"])
        .unique()
        .rename({"assister_name": "name", "assister_steamid": "steamid"})
    )
    assists_ct = (
        kills_with_trades.filter(pl.col("assister_side") == awpy.constants.CT_SIDE)
        .select(["assister_name", "assister_steamid", "round_num"])
        .unique()
        .rename({"assister_name": "name", "assister_steamid": "steamid"})
    )
    assists_t = (
        kills_with_trades.filter(pl.col("assister_side") == awpy.constants.T_SIDE)
        .select(["assister_name", "assister_steamid", "round_num"])
        .unique()
        .rename({"assister_name": "name", "assister_steamid": "steamid"})
    )

    # --- Trades ---

    trades_total = (
        kills_with_trades.filter(pl.col("was_traded"))
        .select(["victim_name", "victim_steamid", "round_num"])
        .unique()
        .rename({"victim_name": "name", "victim_steamid": "steamid"})
    )
    trades_ct = (
        kills_with_trades.filter((pl.col("victim_side") == awpy.constants.CT_SIDE) & (pl.col("was_traded")))
        .select(["victim_name", "victim_steamid", "round_num"])
        .unique()
        .rename({"victim_name": "name", "victim_steamid": "steamid"})
    )
    trades_t = (
        kills_with_trades.filter((pl.col("victim_side") == awpy.constants.T_SIDE) & (pl.col("was_traded")))
        .select(["victim_name", "victim_steamid", "round_num"])
        .unique()
        .rename({"victim_name": "name", "victim_steamid": "steamid"})
    )

    # --- Survivals ---
    # Get the last tick of each round per player, then only keep those with health > 0.
    survivals = demo.ticks.sort("tick").group_by(["name", "steamid", "round_num"]).tail(1).filter(pl.col("health") > 0)
    survivals_total = survivals.select(["name", "steamid", "round_num"]).unique()
    # Depending on your data, team names might be lowercase; adjust as needed.
    survivals_ct = (
        survivals.filter(pl.col("side") == awpy.constants.CT_SIDE).select(["name", "steamid", "round_num"]).unique()
    )
    survivals_t = (
        survivals.filter(pl.col("side") == awpy.constants.T_SIDE).select(["name", "steamid", "round_num"]).unique()
    )

    # --- Tabulate KAST ---
    # Overall ("all"): combine kills, assists, trades, and survivals.
    total_kast = (
        pl.concat([kills_total, assists_total, trades_total, survivals_total])
        .unique()
        .drop_nulls()
        .group_by(["name", "steamid"])
        .agg(pl.count("round_num").alias("kast_rounds"))
        .join(demo.player_round_totals.filter(pl.col("side") == "all"), on=["name", "steamid"], how="left")
        .with_columns((pl.col("kast_rounds") * 100 / pl.col("n_rounds")).alias("kast"))
    )

    # ct side
    ct_kast = (
        pl.concat([kills_ct, assists_ct, trades_ct, survivals_ct])
        .unique()
        .drop_nulls()
        .group_by(["name", "steamid"])
        .agg(pl.count("round_num").alias("kast_rounds"))
        .join(
            demo.player_round_totals.filter(pl.col("side") == awpy.constants.CT_SIDE),
            on=["name", "steamid"],
            how="left",
        )
        .with_columns((pl.col("kast_rounds") * 100 / pl.col("n_rounds")).alias("kast"))
        .with_columns(pl.lit(awpy.constants.CT_SIDE).alias("side"))
    )

    # t side
    t_kast = (
        pl.concat([kills_t, assists_t, trades_t, survivals_t])
        .unique()
        .drop_nulls()
        .group_by(["name", "steamid"])
        .agg(pl.count("round_num").alias("kast_rounds"))
        .join(
            demo.player_round_totals.filter(pl.col("side") == awpy.constants.T_SIDE), on=["name", "steamid"], how="left"
        )
        .with_columns((pl.col("kast_rounds") * 100 / pl.col("n_rounds")).alias("kast"))
        .with_columns(pl.lit(awpy.constants.T_SIDE).alias("side"))
    )

    # Combine all KAST stats
    kast_df = pl.concat([total_kast, ct_kast, t_kast])
    return kast_df.select(["name", "steamid", "side", "kast_rounds", "n_rounds", "kast"])
