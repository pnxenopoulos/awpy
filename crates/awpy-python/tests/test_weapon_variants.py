"""Check weapon variants against real-demo shot events."""

import fixture_store
import polars as pl
import pytest
from awpy import Demo


def _fixture_demo(name: str) -> Demo:
    """Load a named fixture. Fail if an enabled fixture run cannot load it."""
    entry = next((f for f in fixture_store.load_manifest() if f["name"] == name), None)
    if entry is not None:
        demo = fixture_store.get_demo(entry)
        if demo is not None:
            return demo
    message = f"required fixture {name!r} is missing from the manifest or unavailable"
    if fixture_store.download_enabled():
        pytest.fail(message)
    pytest.skip(message)


@pytest.mark.parametrize("enabled", ["0", "1"])
@pytest.mark.parametrize("listed", [False, True])
def test_missing_fixture_fails_only_when_enabled(
    enabled: str, listed: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_RUN_FIXTURES", enabled)
    entries = [{"name": "missing"}] if listed else []
    monkeypatch.setattr(fixture_store, "load_manifest", lambda: entries)
    monkeypatch.setattr(fixture_store, "get_demo", lambda entry: None)
    expected = pytest.fail.Exception if enabled == "1" else pytest.skip.Exception
    with pytest.raises(expected, match="required fixture 'missing'"):
        _fixture_demo("missing")


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
    demo = _fixture_demo(fixture_name)
    _check_loadout(demo, weapon, column)
    assert weapon in demo.item_events["item"].to_list()


@pytest.mark.fixtures
@pytest.mark.parametrize("segments", [1, 4])
def test_kensizor_round_two_revolver(segments: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    demo = _fixture_demo("hltv-de_mirage-2394170")
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
