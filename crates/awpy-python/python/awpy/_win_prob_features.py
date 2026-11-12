"""Build the replay features for the cs2-win-prob Kumo context.

Keep the features the same as ``cs_win_prob.data_preparation``.
"""

from bisect import bisect_left, bisect_right

import polars as pl

from awpy._awpy import Demo

SIDES = ("counter-terrorist", "terrorist")

#: True when a CT or T player attacks a player on the other side.
ENEMY_ATTACK = (
    pl.col("attacker_side").is_in(SIDES)
    & pl.col("victim_side").is_in(SIDES)
    & (pl.col("attacker_side") != pl.col("victim_side"))
)

_TRAINING_MAPS = frozenset(
    {
        "de_ancient",
        "de_anubis",
        "de_cache",
        "de_dust2",
        "de_inferno",
        "de_mirage",
        "de_nuke",
        "de_overpass",
        "de_train",
        "de_vertigo",
    }
)
_PREFIXES = {"t": "terrorist", "ct": "counter-terrorist"}
_RIFLES = ("ak47", "aug", "famas", "galilar", "m4a1", "m4a1_silencer", "sg556")
_SMGS = ("bizon", "mac10", "mp5sd", "mp7", "mp9", "p90", "ump45")


def _alive(prefix: str) -> pl.Expr:
    return (pl.col("side") == _PREFIXES[prefix]) & (pl.col("health") > 0)


def _total(value: pl.Expr) -> pl.Expr:
    return value.cast(pl.Int64).sum()


def _team_features() -> dict[str, pl.Expr]:
    health, armor, primary = pl.col("health"), pl.col("armor"), pl.col("primary_weapon")
    features = {}
    for prefix, side in _PREFIXES.items():
        alive = _alive(prefix)
        features[f"{prefix}_dead"] = (pl.col("side") == side) & (health <= 0)
        for low, high in ((0, 24), (25, 49), (50, 74), (75, 100)):
            features[f"{prefix}_health_{low}_{high}"] = alive & health.is_between(low, high)
            features[f"{prefix}_armor_{low}_{high}"] = alive & armor.is_between(low, high)
        features[f"{prefix}_helmets"] = alive & pl.col("has_helmet")
        for item in ("fire_grenades", "smoke_grenades", "he_grenades", "equipment_value"):
            features[f"{prefix}_{item}"] = pl.col(item).filter(alive)
        features[f"{prefix}_rifles"] = alive & primary.is_in(_RIFLES)
        features[f"{prefix}_smgs"] = alive & primary.is_in(_SMGS)
        features[f"{prefix}_awps"] = alive & (primary == "awp")
    features["ct_defuse_kits"] = _alive("ct") & pl.col("has_defuser")
    return {name: _total(value) for name, value in features.items()}


_TEAM_FEATURES = _team_features()
_BOMB_DISTANCE = pl.sum_horizontal(
    *((pl.col(axis) - pl.col(f"_bomb_{axis}")) ** 2 for axis in "xyz"), ignore_nulls=False
).sqrt()
_PLAYER_FEATURES = {
    **_TEAM_FEATURES,
    "t_live_hp": _total(pl.col("health").filter(_alive("t"))),
    "ct_live_hp": _total(pl.col("health").filter(_alive("ct"))),
    "t_flashbangs": _total(pl.col("flashbangs").filter(_alive("t"))),
    "ct_flashbangs": _total(pl.col("flashbangs").filter(_alive("ct"))),
    "defuse_in_progress": (
        _alive("ct") & pl.col("_plant_tick").is_not_null() & pl.col("is_defusing")
    ).any(),
    "ct_distance_to_bomb": _BOMB_DISTANCE.filter(_alive("ct")).min(),
    "t_distance_to_bomb": _BOMB_DISTANCE.filter(_alive("t")).min(),
}

#: The features that all contexts contain.
BASE_FEATURE_COLUMNS = ("map", "phase", "time_since_phase_start", *_TEAM_FEATURES)
#: All features in context order. A context can omit features after the base features.
FEATURE_COLUMNS = (
    *BASE_FEATURE_COLUMNS,
    "t_live_hp",
    "ct_live_hp",
    "t_flashbangs",
    "ct_flashbangs",
    "bombsite",
    "defuse_in_progress",
    "ct_distance_to_bomb",
    "t_distance_to_bomb",
)


def recording_for(demo: Demo, part: int | None) -> Demo:
    """Select one recording, so that round numbers and ticks are not ambiguous."""
    if part is None:
        if len(demo.paths) != 1:
            raise ValueError("specify part for a multipart demo")
        return demo
    if type(part) is not int or not 0 <= part < len(demo.paths):
        raise ValueError("part must be a valid zero-based recording index")
    return demo.parts[part]


def round_windows(demo: Demo, round_num: int | None = None) -> pl.DataFrame:
    """Return the live interval of each completed round, sorted by freeze end.

    The intervals do not use round outcomes. If ``round_num`` is set, return
    only that round, or raise ``ValueError`` if it is not one completed round.
    """
    windows = (
        demo.rounds.select("round_num", "freeze_end_tick", "end_tick")
        .filter(pl.col("freeze_end_tick") <= pl.col("end_tick"))
        .sort("freeze_end_tick")
    )
    if round_num is None:
        return windows
    windows = windows.filter(pl.col("round_num") == round_num)
    if windows.height != 1:
        raise ValueError(f"expected one completed round {round_num} in the recording")
    return windows


def planted_bombs(demo: Demo) -> pl.DataFrame:
    """Return completed plants. The planter position is the C4 position estimate."""
    demo.load("bomb")
    return (
        demo.bomb.filter(pl.col("event") == "finish_plant")
        .select(
            pl.col("tick").alias("_plant_tick"),
            "bombsite",
            *(pl.col(axis).cast(pl.Float64).alias(f"_bomb_{axis}") for axis in "xyz"),
        )
        .unique(subset="_plant_tick", keep="first")
        .sort("_plant_tick")
    )


def features_at(demo: Demo, ticks: list[int]) -> pl.DataFrame:
    """Build the model inputs at sorted, unique ticks.

    Omit the ticks that have no CT or T player snapshot.
    """
    rounds = round_windows(demo)
    numbers, starts, ends = (rounds[name].to_list() for name in rounds.columns)
    plants = planted_bombs(demo)
    plant_ticks = plants["_plant_tick"].to_list()
    tick_rate = demo.tick_rate
    map_name = demo.header.get("map_name")
    if map_name not in _TRAINING_MAPS:
        map_name = "other"
    rows = []
    for tick in ticks:
        index = bisect_right(starts, tick) - 1
        if index < 0 or tick > ends[index]:
            raise ValueError(f"tick {tick} is outside a completed round's live interval")
        start = starts[index]
        # Use the first plant after freeze end, but only after the plant completes.
        first = bisect_left(plant_ticks, start)
        plant = (
            plant_ticks[first] if first < len(plant_ticks) and plant_ticks[first] <= tick else None
        )
        phase = "bomb_not_planted" if plant is None else "bomb_planted"
        elapsed = (tick - (start if plant is None else plant)) / tick_rate
        rows.append((tick, numbers[index], plant, map_name, phase, elapsed))
    samples = pl.DataFrame(
        rows,
        schema={
            "tick": pl.Int32,
            "round_num": pl.Int32,
            "_plant_tick": pl.Int32,
            "map": pl.String,
            "phase": pl.String,
            "time_since_phase_start": pl.Float64,
        },
        orient="row",
    ).join(plants, on="_plant_tick", how="left", maintain_order="left")

    players = (
        demo.snapshots(ticks=ticks)
        .filter(pl.col("side").is_in(SIDES))
        .join(samples.select("tick", "_plant_tick", "_bomb_x", "_bomb_y", "_bomb_z"), on="tick")
    )
    return samples.join(
        players.group_by("tick").agg(**_PLAYER_FEATURES), on="tick", maintain_order="left"
    ).select("tick", "round_num", *FEATURE_COLUMNS)
