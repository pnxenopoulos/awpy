"""Module for round parsing functions."""

import polars as pl

import awpy.constants
import awpy.converters
import awpy.parsers.utils


def _find_valid_round_indices(rounds_df: pl.DataFrame, full_sequence: list[str]) -> list[int]:
    """Identify indices in the rounds DataFrame that form a valid round sequence.

    A valid sequence is defined as either:
      - A full sequence matching: ["start", "freeze_end", "end", "official_end"]
      - An incomplete sequence matching either:
          ["start", "freeze_end", "end"],
          ["start", "end", "official_end"], or
          ["start", "end"] (typically occurring when there's a surrender vote)
      - If at the end of the DataFrame only the first 3 events of full_sequence are present
        (i.e. ["start", "freeze_end", "end"]), consider that valid.

    Args:
        rounds_df: DataFrame containing event rows with an "event" column.
        full_sequence: The expected full sequence of events.

    Returns:
        A list of row indices in rounds_df that are part of a valid sequence.
    """
    valid_indices = []
    sequence_length_full = len(full_sequence)  # Expected full sequence length (4)
    alt_sequence1 = ["start", "freeze_end", "end"]
    alt_sequence2 = ["start", "end", "official_end"]
    alt_sequence3 = ["start", "end"]  # For surrender vote

    n_rows = len(rounds_df)
    for i in range(n_rows):
        # Extract a slice of events; if we're near the end, this may be shorter than full_sequence.
        current_sequence = rounds_df["event"].slice(i, sequence_length_full).to_list()

        # 1. Check for a complete round sequence.
        if current_sequence == full_sequence:
            valid_indices.extend(range(i, i + sequence_length_full))
        # 2. Check for a 3-event sequence: ["start", "freeze_end", "end"].
        elif current_sequence == alt_sequence1:
            valid_indices.extend(range(i, i + len(alt_sequence1)))
        # 3. Check for a 3-event sequence: ["start", "end", "official_end"].
        elif len(current_sequence) >= len(alt_sequence2) and current_sequence[: len(alt_sequence2)] == alt_sequence2:
            valid_indices.extend(range(i, i + len(alt_sequence2)))
        # 4. Check for a 2-event sequence: ["start", "end"].
        elif len(current_sequence) == len(alt_sequence3) and current_sequence == alt_sequence3:
            valid_indices.extend(range(i, i + len(alt_sequence3)))
        # 5. Lastly, if we're at the very end and only have 3 events, check if they match the first three events of full
        elif (
            len(current_sequence) < sequence_length_full
            and len(current_sequence) == 3
            and current_sequence == full_sequence[:3]
        ):
            valid_indices.extend(range(i, i + len(current_sequence)))

    return valid_indices


def _add_bomb_plant_info(rounds_df: pl.DataFrame, bomb_plants: pl.DataFrame) -> pl.DataFrame:
    """Add bomb plant tick and site information to the rounds DataFrame.

    For each round, this function looks for bomb plant events occurring between
    the round's start and end ticks. It then adds two new columns:
      - bomb_plant: The tick at which the bomb was planted (if any).
      - bomb_site: "bombsite_a" or "bombsite_b" based on the site value, or "not planted"
        if no bomb plant occurred.

    Args:
        rounds_df: DataFrame containing round information with "start" and "end" columns.
        bomb_plants: DataFrame of bomb planted events.

    Returns:
        Updated rounds_df with additional bomb plant information.
    """
    n_rounds = len(rounds_df)
    bomb_plant_ticks = [None] * n_rounds
    bomb_plant_sites = ["not_planted"] * n_rounds

    # If no bomb plant events are provided, return the rounds DataFrame as is.
    if bomb_plants.is_empty():
        return rounds_df

    for i in range(n_rounds):
        start_tick = rounds_df["start"][i]
        end_tick = rounds_df["end"][i]
        # Filter bomb plant events that occur within the current round's tick range.
        plant_events = bomb_plants.filter((pl.col("tick") >= start_tick) & (pl.col("tick") <= end_tick))
        if len(plant_events) > 0:
            # Use the first bomb plant event for this round.
            bomb_plant_ticks[i] = plant_events["tick"][0]
            bomb_plant_sites[i] = "bombsite_a" if plant_events["site"][0] == 220 else "bombsite_b"

    # Add the bomb plant information as new columns.
    return rounds_df.with_columns(
        [
            pl.Series(name="bomb_plant", values=bomb_plant_ticks),
            pl.Series(name="bomb_site", values=bomb_plant_sites),
        ]
    )


def create_round_df(events: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Create a consolidated rounds DataFrame from a dictionary of event DataFrames.

    This function processes round events (start, freeze_end, end, official_end) from the input,
    filters and validates the event sequence, and pivots the data to create a structured round
    DataFrame. It also integrates bomb plant events to add bomb planting tick and site information.

    Args:
        events (dict[str, pl.DataFrame]): A dictionary containing event DataFrames with keys:
            - "round_start"
            - "round_end"
            - "round_end_official"
            - "round_freeze_end"
            Optionally:
            - "bomb_planted"

    Returns:
        pl.DataFrame: A DataFrame representing consolidated round information.

    Raises:
        KeyError: If any required event key is missing from the events dictionary.
        ValueError: If no valid round sequences are found in the processed event data.
    """
    # Retrieve required event DataFrames.
    round_start = awpy.parsers.utils.get_event_from_parsed_events(events, "round_start")
    round_end = awpy.parsers.utils.get_event_from_parsed_events(events, "round_end")
    round_end_official = awpy.parsers.utils.get_event_from_parsed_events(events, "round_officially_ended")
    round_freeze_end = awpy.parsers.utils.get_event_from_parsed_events(events, "round_freeze_end")

    # Retrieve optional bomb planted events; default to empty DataFrame if missing.
    bomb_plants = events.get("bomb_planted", pl.DataFrame())

    # Extract only the 'event' and 'tick' columns from each round event DataFrame.
    event_dfs = [
        round_start[["event", "tick"]],
        round_freeze_end[["event", "tick"]],
        round_end[["event", "tick"]],
        round_end_official[["event", "tick"]],
    ]

    # Concatenate event DataFrames and filter out rows with tick==0 (unless event is "start").
    rounds_df = pl.concat(event_dfs).filter(~((pl.col("tick") == 0) & (pl.col("event") != "start")))

    # Define an enumeration for event types.
    round_events_enum = pl.Enum(["official_end", "start", "freeze_end", "end"])

    # Reconstruct the DataFrame with the event type override, remove duplicates, and sort.
    rounds_df = (
        pl.DataFrame(rounds_df, schema_overrides={"event": round_events_enum})
        .unique(subset=["tick", "event"])
        .sort(by=["tick", "event"])
    )

    # Define the expected full event sequence.
    expected_full_sequence = ["start", "freeze_end", "end", "official_end"]

    # Identify the indices of rows that form valid round sequences.
    valid_indices = _find_valid_round_indices(rounds_df, expected_full_sequence)
    if not valid_indices:
        no_valid_sequences_err_msg = "No valid round sequences found in the event data."
        raise ValueError(no_valid_sequences_err_msg)

    # Filter the DataFrame to include only rows that are part of valid round sequences.
    rounds_df = rounds_df[valid_indices]

    # Create a round number column by cumulatively summing "start" events.
    rounds_df = rounds_df.with_columns(round_num=(pl.col("event") == "start").cast(pl.Int8).cum_sum())

    # Pivot the DataFrame so that each round is one row with columns for each event type.
    rounds_df = rounds_df.pivot(index="round_num", on="event", values="tick", aggregate_function="first")

    # Join additional round details (such as winner and reason) from the round_end events.
    rounds_df = rounds_df.join(round_end[["tick", "winner", "reason"]], left_on="end", right_on="tick")

    # Replace winner and reason with constants
    rounds_df = (
        rounds_df.with_columns(
            pl.col("winner").str.replace("CT", awpy.constants.CT_SIDE),
        )
        .with_columns(
            pl.col("winner").str.replace("TERRORIST", awpy.constants.T_SIDE),
        )
        .with_columns(
            pl.col("winner").str.replace("T", awpy.constants.T_SIDE),
        )
    )

    # Replace round number with row index (starting at 1) and coalesce official_end data.
    rounds_df = (
        rounds_df.drop("round_num")
        .with_columns(pl.coalesce(pl.col("official_end"), pl.col("end")).alias("official_end"))
        .with_row_index("round_num", offset=1)
    )

    # Integrate bomb plant information into the rounds DataFrame.
    return _add_bomb_plant_info(rounds_df, bomb_plants)


def apply_round_num(df: pl.DataFrame, rounds_df: pl.DataFrame, tick_col: str = "tick") -> pl.DataFrame:
    """Assign a round number to each event based on its tick value.

    For each row in `df`, this function finds the round from `rounds_df`
    in which the event's tick falls. A round is defined by the interval
    [start, end] given in `rounds_df`. If an event's tick does not fall within
    any round interval, the new column will contain null.

    This function uses an asof join on the 'start' column of the rounds DataFrame.
    After joining, it validates that the tick is less than or equal to the round's 'end' tick.

    Args:
        df (pl.DataFrame): Input DataFrame containing an event tick column.
        rounds_df (pl.DataFrame): DataFrame containing round boundaries with at least
            the columns:
                - 'round_num': The round number.
                - 'start': The starting tick of the round.
                - 'end': The ending tick of the round.
            This DataFrame should be sorted in ascending order by the 'start' column.
        tick_col (str, optional): Name of the tick column in `df`. Defaults to "tick".

    Returns:
        pl.DataFrame: A new DataFrame with all the original columns and an added
        "round_num" column that indicates the round in which the event occurs. If no
        matching round is found, "round_num" will be null.
    """
    # Use join_asof to get the round where round.start <= event.tick.
    # This join will add the columns 'round_num', 'start', and 'end' from rounds_df.
    df_with_round = df.join_asof(
        rounds_df.select(["round_num", "start", "official_end"]),
        left_on=tick_col,
        right_on="start",
        strategy="backward",
    )

    # Validate that the event tick is within the round boundaries.
    # If the tick is greater than the round's 'end', then set round_num to null.
    df_with_round = df_with_round.with_columns(
        pl.when(pl.col(tick_col) <= pl.col("official_end")).then(pl.col("round_num")).otherwise(None).alias("round_num")
    )

    return df_with_round.drop(["start", "official_end"])
