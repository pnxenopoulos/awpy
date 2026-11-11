"""Damage rows name the weapon variant, like kills and shots do."""

from collections.abc import Callable
from pathlib import Path

import polars as pl
import pytest
from awpy import Demo
from polars.testing import assert_frame_equal

FAMILIES = (
    ("hkp2000", "usp_silencer"),
    ("m4a1", "m4a1_silencer"),
    ("deagle", "revolver"),
)


def _with_round(frame: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    starts = rounds.select("round_num", pl.col("start_tick").alias("tick")).sort("tick")
    return frame.sort("tick").join_asof(starts, on="tick")


@pytest.mark.parametrize(
    ("match_demo", "variants"),
    [
        ("faceit-de_mirage-6de46e85", {"usp_silencer", "m4a1_silencer"}),
        ("valve-de_mirage-472514809", {"revolver"}),
    ],
    indirect=["match_demo"],
)
def test_damage_variants_match_shots(match_demo: Demo, variants: set[str]) -> None:
    match_demo.load("shots", "damages")
    shots = _with_round(
        match_demo.shots.with_columns(pl.col("weapon").str.replace("^weapon_", "")),
        match_demo.rounds,
    )
    damage = _with_round(match_demo.damages.drop_nulls("attacker_steamid"), match_demo.rounds)
    assert variants <= set(damage["weapon"].unique().to_list())

    keys = ["steamid", "round_num", "weapon"]
    for names in FAMILIES:
        fired = shots.filter(pl.col("weapon").is_in(names)).select(keys).unique()
        hits = (
            damage.filter(pl.col("weapon").is_in(names))
            .rename({"attacker_steamid": "steamid"})
            .select(keys)
            .unique()
        )
        stray = hits.join(fired, on=keys, how="anti")
        assert stray.is_empty(), f"{names}: damage variants never fired:\n{stray}"


@pytest.mark.fixtures
@pytest.mark.parametrize("demo_name", ["faceit-de_mirage-6de46e85", "valve-de_mirage-472514809"])
def test_parallel_damage_matches_serial(
    demo_name: str, demo_file: Callable[[str | None], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = demo_file(demo_name)
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "1")
    serial = Demo(path).damages
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "4")
    parallel = Demo(path).damages
    assert_frame_equal(serial, parallel, check_exact=True)


@pytest.mark.parametrize("match_demo", ["faceit-de_mirage-6de46e85"], indirect=True)
def test_non_variant_weapon_names_are_unchanged(match_demo: Demo) -> None:
    names = set(match_demo.damages["weapon"].unique().to_list())
    assert {"ak47", "hegrenade", "knife"} <= names
