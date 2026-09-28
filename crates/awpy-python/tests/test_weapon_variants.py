"""Check weapon variants against real-demo shot events."""

from pathlib import Path

import polars as pl
import pytest
from awpy import Demo
from fixture_store import get_demo, load_manifest


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
    ("fixture_name", "weapon", "column"),
    [
        ("valve-de_mirage-472514809", "revolver", "secondary_weapon"),
        ("faceit-de_mirage-6de46e85", "deagle", "secondary_weapon"),
        ("faceit-de_mirage-6de46e85", "usp_silencer", "secondary_weapon"),
        ("faceit-de_mirage-6de46e85", "m4a1", "primary_weapon"),
        ("faceit-de_mirage-6de46e85", "m4a1_silencer", "primary_weapon"),
    ],
)
def test_shared_class_loadouts(
    fixture_name: str, weapon: str, column: str, segments: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    entry = next((f for f in load_manifest() if f["name"] == fixture_name), None)
    if entry is None:
        pytest.skip(f"fixture {fixture_name} is not in the manifest")
    demo = get_demo(entry)
    if demo is None:
        pytest.skip(f"fixture {fixture_name} is not cached")
    _check_loadout(demo, weapon, column)


@pytest.mark.parametrize("segments", [1, 4])
def test_kensizor_round_two_revolver(segments: int, monkeypatch: pytest.MonkeyPatch) -> None:
    path = Path(__file__).resolve().parents[3] / "b8-vs-vitality-m1-mirage.dem"
    if not path.is_file():
        pytest.skip("reported B8 Mirage demo is not available")
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    demo = Demo(path)
    round_two = demo.rounds.filter(pl.col("round_num") == 2).row(0, named=True)
    ticks = [15346, 15391]
    assert all(round_two["freeze_end_tick"] <= tick <= round_two["end_tick"] for tick in ticks)
    states = demo.snapshots(ticks=ticks).filter(pl.col("name") == "kensizor").sort("tick")
    assert states["tick"].to_list() == ticks
    assert states["active_weapon"].to_list() == ["revolver", "revolver"]
    assert states["secondary_weapon"].to_list() == ["revolver", "revolver"]
    assert states["inventory"].to_list() == ["knife,revolver", "knife,revolver"]
    shots = demo.shots.filter(pl.col("tick").is_in(ticks) & (pl.col("name") == "kensizor"))
    assert shots["weapon"].to_list() == ["weapon_revolver", "weapon_revolver"]


def test_reported_b8_loadouts() -> None:
    path = Path(__file__).resolve().parents[3] / "b8-vs-vitality-m2-dust2.dem"
    if not path.is_file():
        pytest.skip("reported B8 demo is not available")
    demo = Demo(path)
    _check_loadout(demo, "usp_silencer", "secondary_weapon")
    _check_loadout(demo, "m4a1_silencer", "primary_weapon")
    assert "m4a1_silencer" in demo.item_events["item"].to_list()
