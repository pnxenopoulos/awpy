"""Module to parse bomb location and status."""

import polars as pl

import awpy.parsers.utils


def parse_bomb(events: dict[str, pl.DataFrame], valid_ticks: pl.Series) -> pl.DataFrame:
    """Create a unified bomb location table by combining bomb event data.

    This function extracts bomb-related events from the provided events dictionary for four types of bomb events:
      - "bomb_dropped": indicating that the bomb was dropped.
      - "bomb_pickup": indicating that the bomb was picked up (i.e. carried).
      - "bomb_planted": indicating that the bomb was planted.
      - "bomb_exploded": indicating that the bomb exploded/detonated.
      - "bomb_defused": indicating that the bomb was defused.

    The resulting DataFrame has the following columns:
      - tick: The tick value.
      - event: The bomb status ("drop", "pickup", "plant", "event").
      - x, y, z: The bomb's location coordinates from the ticks DataFrame.
      - steamid: The player's steam ID from the ticks DataFrame.
      - name: The player's name from the ticks DataFrame.
      - bombsite: For planted events, the bombsite (otherwise null).

    Parameters:
        events (dict[str, pl.DataFrame]): A dictionary of parsed event DataFrames. Must contain:
            - "bomb_dropped": DataFrame with columns at least ["entindex", "tick", "user_name", "user_steamid"].
            - "bomb_pickup": DataFrame with columns at least ["tick", "user_name", "user_steamid"].
            - "bomb_planted": DataFrame with columns at least ["site", "tick", "user_name", "user_steamid"].
            - "bomb_exploded": DataFrame with columns at least ["tick", "user_name", "user_steamid"].
            - "bomb_defused": DataFrame with columns at least ["tick", "user_name", "user_steamid"].
        ticks (pl.DataFrame): A DataFrame of tick data containing positional and player information with columns:
            ["tick", "steamid", "name", "X", "Y", "Z"].
        valid_ticks (pl.Series): A Series of valid tick values.

    Returns:
        pl.DataFrame: A DataFrame with one row per tick containing the columns:
            tick, event, x, y, z, steamid, name, bombsite.

    Raises:
        KeyError: If any of the required bomb event DataFrames ("bomb_dropped", "bomb_pickup",
                  "bomb_planted", or "bomb_exploded") are missing from the events dictionary.
        KeyError: If the ticks DataFrame does not contain the required columns.
    """
    # Retrieve required bomb events.
    bomb_dropped = awpy.parsers.utils.get_event_from_parsed_events(events, "bomb_dropped", empty_if_not_found=True)
    bomb_pickup = awpy.parsers.utils.get_event_from_parsed_events(events, "bomb_pickup", empty_if_not_found=True)
    bomb_planted = awpy.parsers.utils.get_event_from_parsed_events(events, "bomb_planted", empty_if_not_found=True)
    bomb_exploded = awpy.parsers.utils.get_event_from_parsed_events(events, "bomb_exploded", empty_if_not_found=True)
    bomb_defused = awpy.parsers.utils.get_event_from_parsed_events(events, "bomb_defused", empty_if_not_found=True)

    # Process bomb_dropped events
    bd = (
        (
            bomb_dropped.with_columns([pl.lit("drop").alias("event"), pl.lit(None).alias("bombsite")])
            .sort("tick")
            .filter(pl.col("tick").is_in(valid_ticks))
            .select(
                [
                    pl.col("tick"),
                    pl.col("event"),
                    pl.col("user_X").alias("X"),
                    pl.col("user_Y").alias("Y"),
                    pl.col("user_Z").alias("Z"),
                    pl.col("user_steamid").alias("steamid"),
                    pl.col("user_name").alias("name"),
                    pl.lit(None).alias("bombsite").cast(pl.Utf8),
                ]
            )
        )
        if not bomb_dropped.is_empty()
        else pl.DataFrame()
    )

    # Process bomb_pickup events
    bp = (
        (
            bomb_pickup.with_columns([pl.lit("pickup").alias("event"), pl.lit(None).alias("bombsite")])
            .sort("tick")
            .filter(pl.col("tick").is_in(valid_ticks))
            .select(
                [
                    pl.col("tick"),
                    pl.col("event"),
                    pl.col("user_X").alias("X"),
                    pl.col("user_Y").alias("Y"),
                    pl.col("user_Z").alias("Z"),
                    pl.col("user_steamid").alias("steamid"),
                    pl.col("user_name").alias("name"),
                    pl.lit(None).alias("bombsite").cast(pl.Utf8),
                ]
            )
        )
        if not bomb_pickup.is_empty()
        else pl.DataFrame()
    )

    # Process bomb_planted events
    bpnt = (
        (
            bomb_planted.with_columns([pl.lit("plant").alias("event")])
            .sort("tick")
            .filter(pl.col("tick").is_in(valid_ticks))
            .select(
                [
                    pl.col("tick"),
                    pl.col("event"),
                    pl.col("user_X").alias("X"),
                    pl.col("user_Y").alias("Y"),
                    pl.col("user_Z").alias("Z"),
                    pl.col("user_steamid").alias("steamid"),
                    pl.col("user_name").alias("name"),
                    pl.col("user_place").alias("bombsite").cast(pl.Utf8),
                ]
            )
        )
        if not bomb_planted.is_empty()
        else pl.DataFrame()
    )

    # Process bomb_exploded events
    bexp = (
        (
            bomb_exploded.with_columns([pl.lit("detonate").alias("event"), pl.lit(None).alias("bombsite")])
            .sort("tick")
            .filter(pl.col("tick").is_in(valid_ticks))
            .select(
                [
                    pl.col("tick"),
                    pl.col("event"),
                    pl.col("user_X").alias("X"),
                    pl.col("user_Y").alias("Y"),
                    pl.col("user_Z").alias("Z"),
                    pl.col("user_steamid").alias("steamid"),
                    pl.col("user_name").alias("name"),
                    pl.lit(None).alias("bombsite").cast(pl.Utf8),
                ]
            )
        )
        if not bomb_exploded.is_empty()
        else pl.DataFrame()
    )

    # Process bomb_defused events
    bdef = (
        (
            bomb_defused.with_columns([pl.lit("defuse").alias("event"), pl.lit(None).alias("bombsite")])
            .sort("tick")
            .filter(pl.col("tick").is_in(valid_ticks))
            .select(
                [
                    pl.col("tick"),
                    pl.col("event"),
                    pl.col("user_X").alias("X"),
                    pl.col("user_Y").alias("Y"),
                    pl.col("user_Z").alias("Z"),
                    pl.col("user_steamid").alias("steamid"),
                    pl.col("user_name").alias("name"),
                    pl.col("user_place").alias("bombsite").cast(pl.Utf8),
                ]
            )
        )
        if not bomb_defused.is_empty()
        else pl.DataFrame()
    )

    # Combine all bomb events into one DataFrame and sort by tick.
    nonempty_dfs = [df for df in [bd, bp, bpnt, bexp, bdef] if not df.is_empty()]
    return pl.concat(nonempty_dfs).sort("tick")
