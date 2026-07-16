"""Tests for the ``awpy`` CLI (offline; awpy.data and Demo are stubbed)."""

import json
from pathlib import Path

import polars as pl
import pytest
from awpy import InvalidDemoError, cli, data
from typer.testing import CliRunner

runner = CliRunner()


# --- map-data cache commands ---------------------------------------------------


def test_get_downloads_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_update(version=None, *, force=False):
        called["version"], called["force"] = version, force
        out = tmp_path / "2000873"
        out.mkdir()
        (out / "manifest.json").write_text(json.dumps({"maps": ["de_inferno", "de_nuke"]}))
        return out

    monkeypatch.setattr(data, "update", fake_update)
    result = runner.invoke(cli.app, ["get", "2000873", "--force"])
    assert result.exit_code == 0
    assert called == {"version": 2000873, "force": True}
    assert "2 maps" in result.output


def test_get_defaults_to_latest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_update(version=None, *, force=False):
        assert version is None and not force
        out = tmp_path / "42"
        out.mkdir()
        (out / "manifest.json").write_text(json.dumps({"maps": []}))
        return out

    monkeypatch.setattr(data, "update", fake_update)
    assert runner.invoke(cli.app, ["get"]).exit_code == 0


def test_versions_flags_newer_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data, "local_versions", lambda: ["999", "2000873"])
    monkeypatch.setattr(data, "latest_version", lambda: "2000874")
    result = runner.invoke(cli.app, ["versions"])
    assert result.exit_code == 0
    assert "2000873  (newest local)" in result.output
    assert "latest release is 2000874" in result.output


def test_versions_offline_still_lists_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> str:
        raise RuntimeError("no network")

    monkeypatch.setattr(data, "local_versions", lambda: ["2000873"])
    monkeypatch.setattr(data, "latest_version", boom)
    result = runner.invoke(cli.app, ["versions"])
    assert result.exit_code == 0
    assert "2000873  (newest local)" in result.output
    assert "latest release" not in result.output


def test_maps_lists_release_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data, "available_maps", lambda version=None: ["de_dust2", "de_mirage"])
    result = runner.invoke(cli.app, ["maps"])
    assert result.exit_code == 0
    assert result.output == "de_dust2\nde_mirage\n"


def test_clear_one_release(monkeypatch: pytest.MonkeyPatch) -> None:
    cleared = []
    monkeypatch.setattr(data, "clear", cleared.append)
    assert runner.invoke(cli.app, ["clear", "2000873"]).exit_code == 0
    assert cleared == [2000873]


def test_clear_all(monkeypatch: pytest.MonkeyPatch) -> None:
    cleared = []
    monkeypatch.setattr(data, "clear", cleared.append)
    assert runner.invoke(cli.app, ["clear", "--all"]).exit_code == 0
    assert cleared == [None]


def test_clear_without_target_errors() -> None:
    result = runner.invoke(cli.app, ["clear"])
    assert result.exit_code == 2  # usage error


# --- demo inspection commands (Demo stubbed) ------------------------------------


class FakeEvents:
    """Stands in for the Events accessor: two event types with canned frames."""

    frames = {
        "player_death": pl.DataFrame({"tick": [1, 2]}),
        "round_end": pl.DataFrame({"tick": [5]}),
    }

    names = ["player_death", "round_end"]
    counts = {"player_death": 2, "round_end": 1}

    def __contains__(self, name):
        return name in self.frames

    def __getitem__(self, name):
        return self.frames[name]


class FakeDemo:
    """Stands in for awpy.Demo; returns canned frames without touching the file."""

    def __init__(self, path):
        self.path = path

    @property
    def header(self):
        return {"map_name": "de_test", "build_num": 14000}

    @property
    def events(self):
        return FakeEvents()

    @property
    def kills(self):
        return pl.DataFrame({"tick": [10, 20, 30], "attacker_name": ["a", "b", "c"]})

    @property
    def blinds(self):
        return pl.DataFrame(
            {"tick": [5, 15], "victim_name": ["a", "b"], "duration": [1.5, 3.0]}
        )

    @property
    def item_events(self):
        return pl.DataFrame(
            {"tick": [5, 15], "action": ["purchase", "drop"], "item": ["ak47", "ak47"]}
        )


@pytest.fixture
def fake_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch cli.Demo with FakeDemo and return a path that satisfies exists=True."""
    monkeypatch.setattr(cli, "Demo", FakeDemo)
    dem = tmp_path / "match.dem"
    dem.write_bytes(b"\x00")
    return dem


def test_info_table(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["info", str(fake_demo)])
    assert result.exit_code == 0
    assert "de_test" in result.output


def test_info_json(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["info", str(fake_demo), "--json"])
    assert json.loads(result.output)["build_num"] == 14000


def test_kills_json_respects_limit(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["kills", str(fake_demo), "--limit", "2", "--json"])
    rows = json.loads(result.output)
    assert [r["tick"] for r in rows] == [10, 20]


def test_kills_table_shows_all_rows(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["kills", str(fake_demo)])
    assert result.exit_code == 0
    assert "attacker_name" in result.output


def test_blinds_json(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["blinds", str(fake_demo), "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert [r["duration"] for r in rows] == [1.5, 3.0]


def test_item_events_json(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["item-events", str(fake_demo), "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert [r["action"] for r in rows] == ["purchase", "drop"]


def test_events_lists_names(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["events", str(fake_demo)])
    assert result.output == "player_death\nround_end\n"


def test_events_summary_counts(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["events", str(fake_demo), "--summary", "--json"])
    rows = {r["event"]: r["count"] for r in json.loads(result.output)}
    assert rows == {"player_death": 2, "round_end": 1}


def test_events_dumps_named_event(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["events", str(fake_demo), "round_end", "--json"])
    assert json.loads(result.output) == [{"tick": 5}]


def test_events_unknown_name_errors(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["events", str(fake_demo), "player_ping"])
    assert result.exit_code == 1


def test_verify_valid(fake_demo: Path) -> None:
    result = runner.invoke(cli.app, ["verify", str(fake_demo)])
    assert result.exit_code == 0
    assert "Valid demo file" in result.output


def test_verify_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class BadDemo:
        def __init__(self, path):
            raise InvalidDemoError("bad magic bytes")

    monkeypatch.setattr(cli, "Demo", BadDemo)
    dem = tmp_path / "bad.dem"
    dem.write_bytes(b"\x00")
    result = runner.invoke(cli.app, ["verify", str(dem)])
    assert result.exit_code == 1


def test_missing_file_is_usage_error(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["kills", str(tmp_path / "nope.dem")])
    assert result.exit_code == 2


# --- integration: a real demo, if one is present in tests/fixtures/ -------------


def test_kills_on_real_demo(demo_path: Path) -> None:
    result = runner.invoke(cli.app, ["kills", str(demo_path), "--limit", "5", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert 0 < len(rows) <= 5
    assert "attacker_name" in rows[0]
