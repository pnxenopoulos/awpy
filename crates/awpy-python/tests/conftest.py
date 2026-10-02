"""Shared test fixtures.

Cache verified paths for the session. Keep parsed demos only for one module
or parameter. Tests that change parser state must create their own Demo.
"""

from collections.abc import Callable
from functools import cache
from pathlib import Path

import fixture_store
import pytest
from awpy import Demo, data

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def asset_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use an empty local asset cache for this test."""
    monkeypatch.setattr(data, "AWPY_DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_latest_cache", None)
    return tmp_path


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Put all demo-backed tests in the CI fixture job."""
    for item in items:
        if {"demo_path", "match_demo"}.intersection(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.fixtures)


@pytest.fixture(scope="session")
def demo_file() -> Callable[[str | None], Path]:
    """Verify each named demo once. Do not keep parsed demos in this cache."""

    @cache
    def resolve(name: str | None) -> Path:
        entry = next((f for f in fixture_store.load_manifest() if f["name"] == name), None)
        if entry is not None:
            path = fixture_store.ensure_demo(entry)
            if path is not None:
                return path
        message = (
            "fixture manifest has no ground-truth cases"
            if name is None
            else f"required fixture {name!r} is missing from the manifest or unavailable"
        )
        if fixture_store.download_enabled():
            pytest.fail(message, pytrace=False)
        pytest.skip(message)

    return resolve


@pytest.fixture(scope="session")
def demo_path(demo_file: Callable[[str | None], Path]) -> Path:
    """Use the smallest local demo, or the smallest demo in the manifest."""
    local = list(FIXTURES_DIR.glob("*.dem"))
    if local:
        return min(local, key=lambda path: (path.stat().st_size, path.name))
    entries = fixture_store.load_manifest()
    if entries:
        smallest = min(entries, key=lambda entry: entry.get("size", float("inf")))
        return demo_file(smallest["name"])
    if fixture_store.download_enabled():
        pytest.fail("demo fixture manifest is missing or empty", pytrace=False)
    pytest.skip("no demo fixture available; set AWPY_RUN_FIXTURES=1 to allow downloads")


@pytest.fixture(scope="module")
def demo(demo_path: Path) -> Demo:
    """Share a demo for read-only checks. Do not change its cached DataFrames."""
    return Demo(demo_path)


@pytest.fixture(scope="module")
def match_demo(request: pytest.FixtureRequest, demo_file: Callable[[str | None], Path]) -> Demo:
    """Load one manifest demo per parameter, then release its parsed data."""
    return Demo(demo_file(request.param))
