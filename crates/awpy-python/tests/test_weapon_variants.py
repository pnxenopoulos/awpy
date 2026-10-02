"""Check weapon variants against real-demo shot events."""

import polars as pl
import pytest
from awpy import Demo


def _check_loadout(demo: Demo, weapon: str, column: str) -> None:
    shots = demo.shots.filter(pl.col("weapon") == f"weapon_{weapon}").drop_nulls("steamid").head(5)
    assert shots.height > 0, f"fixture has no {weapon} shots"
    states = demo.snapshots(ticks=shots["tick"].unique().to_list())
    for shot in shots.iter_rows(named=True):
        rows = states.filter(
            (pl.col("tick") == shot["tick"]) & (pl.col("steamid") == shot["steamid"])
        )
        assert rows.height == 1
        state = rows.row(0, named=True)
        assert state["active_weapon"] == weapon
        assert state[column] == weapon
        assert weapon in state["inventory"].split(",")


@pytest.mark.fixtures
@pytest.mark.parametrize("segments", [1, 4])
@pytest.mark.parametrize(
    ("match_demo", "weapon", "column"),
    [
        ("valve-de_mirage-472514809", "revolver", "secondary_weapon"),
        ("faceit-de_mirage-6de46e85", "deagle", "secondary_weapon"),
        ("faceit-de_mirage-6de46e85", "usp_silencer", "secondary_weapon"),
        ("faceit-de_mirage-6de46e85", "m4a1", "primary_weapon"),
        ("faceit-de_mirage-6de46e85", "m4a1_silencer", "primary_weapon"),
    ],
    indirect=["match_demo"],
    scope="module",
)
def test_shared_class_loadouts(
    match_demo: Demo, weapon: str, column: str, segments: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    _check_loadout(match_demo, weapon, column)
    assert weapon in match_demo.item_events["item"].to_list()


@pytest.mark.fixtures
@pytest.mark.parametrize("match_demo", ["valve-de_mirage-472514809"], indirect=True)
def test_reload_fields_on_demo_before_quiet_reload_update(match_demo: Demo) -> None:
    states = match_demo.snapshots(every=64)
    assert states.height > 0
    assert states["is_reloading"].dtype == pl.Boolean
    assert states["is_reloading"].any()
    assert states["is_reloading"].eq(False).any()
    assert states["is_silent_reloading"].dtype == pl.Boolean
    armed = states.filter(pl.col("active_weapon").is_not_null())
    assert armed.height > 0
    assert armed["is_silent_reloading"].null_count() == armed.height

    unarmed = states.filter(pl.col("active_weapon").is_null())
    assert unarmed.height > 0
    for name in ("is_reloading", "is_silent_reloading"):
        assert unarmed[name].null_count() == 0
        assert unarmed[name].eq(False).all()


@pytest.mark.fixtures
@pytest.mark.parametrize("segments", [1, 4])
@pytest.mark.parametrize("match_demo", ["hltv-de_mirage-2394170"], indirect=True)
def test_kensizor_round_two_revolver(
    match_demo: Demo, segments: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    round_two = match_demo.rounds.filter(pl.col("round_num") == 2).row(0, named=True)
    ticks = [15346, 15391]
    assert all(round_two["freeze_end_tick"] <= tick <= round_two["end_tick"] for tick in ticks)
    states = match_demo.snapshots(ticks=ticks).filter(pl.col("name") == "kensizor").sort("tick")
    assert states["tick"].to_list() == ticks
    assert states["active_weapon"].to_list() == ["revolver", "revolver"]
    assert states["secondary_weapon"].to_list() == ["revolver", "revolver"]
    assert states["inventory"].to_list() == ["knife,revolver", "knife,revolver"]
    shots = match_demo.shots.filter(pl.col("tick").is_in(ticks) & (pl.col("name") == "kensizor"))
    assert shots["weapon"].to_list() == ["weapon_revolver", "weapon_revolver"]
