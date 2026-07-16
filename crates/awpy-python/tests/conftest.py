"""Shared pytest fixtures.

Demo fixtures are large and not committed. Any ``.dem`` file placed in
``tests/fixtures/`` is discovered automatically; tests that need one are skipped
when the directory is empty (e.g. in a fresh checkout).
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "fixtures: ground-truth tests against downloaded demo fixtures "
        "(opt-in; set AWPY_RUN_FIXTURES=1 to fetch — see tests/fixture_store.py)",
    )


def _demo_files() -> list[Path]:
    if not FIXTURES_DIR.is_dir():
        return []
    return sorted(FIXTURES_DIR.glob("*.dem"))


@pytest.fixture(scope="session")
def demo_path() -> Path:
    """A demo to run the (map-agnostic) schema tests against.

    Prefers any local ``.dem`` in ``tests/fixtures/`` for fast local runs.
    Otherwise falls back to the **smallest** fixture in the manifest — fetched
    only when ``AWPY_RUN_FIXTURES`` is set (see :mod:`fixture_store`), so this is
    the same download source as the ground-truth bench. Skips when neither is
    available.
    """
    local = _demo_files()
    if local:
        return local[0]

    from fixture_store import ensure_demo, load_manifest

    fixtures = load_manifest()
    if fixtures:
        smallest = min(fixtures, key=lambda f: f.get("size", float("inf")))
        path = ensure_demo(smallest)
        if path is not None:
            return path
    pytest.skip("no demo fixture available (none local; set AWPY_RUN_FIXTURES=1 to download)")
