"""Check fixture loading without network access or large demo files."""

from collections.abc import Callable
from pathlib import Path

import fixture_store
import pytest


@pytest.mark.parametrize("enabled", ["0", "1"])
@pytest.mark.parametrize("name, listed", [(None, False), ("missing", False), ("missing", True)])
def test_missing_fixture_fails_only_when_enabled(
    demo_file: Callable[[str | None], Path],
    enabled: str,
    name: str | None,
    listed: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWPY_RUN_FIXTURES", enabled)
    entries = [{"name": name}] if listed else []
    monkeypatch.setattr(fixture_store, "load_manifest", lambda: entries)
    monkeypatch.setattr(fixture_store, "ensure_demo", lambda entry: None)
    expected = pytest.fail.Exception if enabled == "1" else pytest.skip.Exception
    message = "no ground-truth cases" if name is None else "required fixture 'missing'"
    with pytest.raises(expected, match=message):
        demo_file(name)


def test_demo_file_verifies_once(
    demo_file: Callable[[str | None], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    path = tmp_path / "match.dem"
    entry = {"name": "cache-probe"}
    monkeypatch.setattr(fixture_store, "load_manifest", lambda: [entry])

    def ensure(found: dict) -> Path:
        calls.append(found)
        return path

    monkeypatch.setattr(fixture_store, "ensure_demo", ensure)
    assert demo_file("cache-probe") == path
    assert demo_file("cache-probe") == path
    assert calls == [entry]


@pytest.mark.parametrize("state", ["empty", "unavailable", "ready"])
def test_prefetch_requires_all_demos(
    state: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AWPY_RUN_FIXTURES", "0")
    entries = [] if state == "empty" else [{"name": "prefetch-probe"}]
    monkeypatch.setattr(fixture_store, "load_manifest", lambda: entries)

    def ensure(entry: dict) -> Path | None:
        assert fixture_store.download_enabled()
        assert entry == entries[0]
        return tmp_path / "match.dem" if state == "ready" else None

    monkeypatch.setattr(fixture_store, "ensure_demo", ensure)
    if state == "ready":
        fixture_store.main()
        assert capsys.readouterr().out == "ok   prefetch-probe\n"
    else:
        message = "manifest is missing or empty" if state == "empty" else "is unavailable"
        with pytest.raises(SystemExit, match=message):
            fixture_store.main()
