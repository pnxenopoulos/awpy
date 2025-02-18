"""Module for grenade (inferno and smoke) parsing."""

from collections import defaultdict

import polars as pl

import awpy.parsers.utils


def parse_timed_grenade_entity(
    start_df: pl.DataFrame, end_df: pl.DataFrame, max_duration_ticks: int | None = None
) -> pl.DataFrame:
    """Parse timed grenade events (e.g. smokes or infernos) from start and end DataFrames.

    For each grenade start event (from start_df), this function finds the corresponding grenade
    end event (from end_df) for the same grenade (matched on 'entityid') with an 'end_tick' greater
    than the 'start_tick'. If no matching end event is found, 'end_tick' will be null.

    Additionally, if a grenade event's duration (end_tick - start_tick) exceeds the specified
    max_duration (if provided), the end_tick is set to null.

    The resulting DataFrame will have one row per grenade event with the following columns:
      - entity_id: The grenade's entity id.
      - start_tick: The tick at which the grenade event started.
      - end_tick: The tick at which the grenade event ended (or null if not found or if duration is too long).
      - All columns from the start event that begin with "thrower_".
      - X, Y, Z: The coordinates associated with the grenade event.

    Parameters:
        start_df (pl.DataFrame): DataFrame of grenade start events.
        end_df (pl.DataFrame): DataFrame of grenade end events.
        max_duration_ticks (int, optional): Maximum allowed duration in ticks (end_tick - start_tick).
            If the duration exceeds this value, end_tick is set to null. Defaults to None (no filtering).

    Returns:
        pl.DataFrame: A DataFrame with one row per grenade event, including the columns described above.

    Raises:
        KeyError: If any required columns are missing in start_df or end_df.
    """
    # Validate required columns for start_df and end_df.
    required_start = {"entityid", "tick", "user_name", "user_steamid", "x", "y", "z"}
    awpy.parsers.utils.validate_required_columns(start_df, required_start, "start_df")
    awpy.parsers.utils.validate_required_columns(end_df, {"entityid", "tick"}, "end_df")

    # Add a row identifier to start_df (for traceability, if needed)
    sd = start_df.with_row_index("start_idx")

    # Rename columns in start_df to match the desired output.
    # First, rename columns starting with "user_" to "thrower_"
    sd = awpy.parsers.utils.rename_columns_with_affix(sd, old_affix="user_", new_affix="thrower_").rename(
        {"entityid": "entity_id", "tick": "start_tick", "x": "X", "y": "Y", "z": "Z"}
    )

    # Prepare the end events DataFrame:
    # Rename 'tick' to 'end_tick' (and keep the original 'entityid' for matching)
    ed = end_df.rename({"tick": "end_tick"})

    # Convert the DataFrames to lists of dicts for row-wise processing.
    start_list = sd.to_dicts()
    end_list = ed.to_dicts()

    # Group end events by 'entityid' for fast lookup.
    end_by_entity = defaultdict(list)
    for row in end_list:
        end_by_entity[row["entityid"]].append(row["end_tick"])
    # Sort the tick values for each entity (if there are multiple end events).
    for entity in end_by_entity:
        end_by_entity[entity].sort()

    matched_rows = []
    # Loop over each grenade start event.
    for row in start_list:
        entity = row["entity_id"]
        start_tick = row["start_tick"]

        # Get candidate end ticks for this entity.
        candidate_ticks = end_by_entity.get(entity, [])
        # Filter candidate ticks to only those greater than start_tick.
        valid_ticks = [tick for tick in candidate_ticks if tick > start_tick]
        # Select the earliest valid tick, if any.
        end_tick = min(valid_ticks) if valid_ticks else None

        # If max_duration is specified and the duration is too long, set end_tick to None.
        if max_duration_ticks is not None and end_tick is not None and (end_tick - start_tick) > max_duration_ticks:
            end_tick = None

        # Build the combined row.
        combined_row = {
            "entity_id": entity,
            "start_tick": start_tick,
            "end_tick": end_tick,
        }
        # Include all columns from row that start with "thrower_"
        for key, value in row.items():
            if key.startswith("thrower_"):
                combined_row[key] = value

        # Also add coordinate columns.
        for coord in ["X", "Y", "Z"]:
            combined_row[coord] = row[coord]

        matched_rows.append(combined_row)

    # Return the result as a new Polars DataFrame.
    return pl.DataFrame(matched_rows)
