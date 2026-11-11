"""Damage rows name the weapon variant, like kills and shots do."""

import polars as pl
import pytest
from awpy import Demo

FAMILIES = {
    "usp": ("hkp2000", "usp_silencer"),
    "m4": ("m4a1", "m4a1_silencer"),
    "deagle": ("deagle", "revolver"),
}


def _with_round(frame: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    starts = rounds.select("round_num", pl.col("start_tick").alias("tick")).sort("tick")
    return frame.sort("tick").join_asof(starts, on="tick")


def _check_variants_were_fired(demo: Demo) -> None:
    """Every (attacker, round, variant) seen in damages was also fired in shots."""
    shots = _with_round(
        demo.shots.with_columns(pl.col("weapon").str.replace("^weapon_", "")), demo.rounds
    )
    dmg = _with_round(demo.damages.drop_nulls("attacker_name"), demo.rounds)
    for names in FAMILIES.values():
        held = (
            shots.filter(pl.col("weapon").is_in(names))
            .select("name", "round_num", "weapon")
            .unique()
        )
        hits = (
            dmg.filter(pl.col("weapon").is_in(names))
            .select(pl.col("attacker_name").alias("name"), "round_num", "weapon")
            .unique()
        )
        stray = hits.join(held, on=["name", "round_num", "weapon"], how="anti")
        assert stray.height == 0, f"{names}: damage variants never fired:\n{stray}"


@pytest.mark.fixtures
@pytest.mark.parametrize("segments", [1, 4])
@pytest.mark.parametrize("match_demo", ["faceit-de_mirage-6de46e85"], indirect=True)
def test_damage_variants_match_shots(
    match_demo: Demo, segments: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    _check_variants_were_fired(match_demo)
    names = set(match_demo.damages["weapon"].unique().to_list())
    assert {"usp_silencer", "m4a1_silencer"} <= names


@pytest.mark.fixtures
@pytest.mark.parametrize("segments", [1, 4])
@pytest.mark.parametrize("match_demo", ["valve-de_mirage-472514809"], indirect=True)
def test_revolver_damage_is_not_a_deagle(
    match_demo: Demo, segments: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    _check_variants_were_fired(match_demo)
    assert match_demo.damages.filter(pl.col("weapon") == "revolver").height > 0


@pytest.mark.fixtures
@pytest.mark.parametrize("match_demo", ["faceit-de_mirage-6de46e85"], indirect=True)
def test_non_variant_weapon_names_are_unchanged(match_demo: Demo) -> None:
    names = set(match_demo.damages["weapon"].unique().to_list())
    assert {"ak47", "hegrenade", "knife"} <= names
