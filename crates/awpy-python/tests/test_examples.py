"""Smoke-test the scripts in ``examples/``.

Documentation that isn't executed rots. Each example is run as a subprocess
against a real demo — the same fixture the other demo-backed tests use — and is
required to exit 0 and print something. These are deliberately shallow: they
assert the examples still *run* against the current API, not that their numbers
are right (the stats themselves are covered by ``test_demo.py`` and
``test_ground_truth.py``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Scripts that only need the base install. `clutch_reel.py` is handled separately
# because it needs matplotlib and writes image files.
SIMPLE_EXAMPLES = ["scoreboard.py", "trades.py", "economy.py"]


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def test_examples_dir_is_complete() -> None:
    """Every example is either smoke-tested or explicitly accounted for."""
    on_disk = {p.name for p in EXAMPLES_DIR.glob("*.py")}
    covered = {*SIMPLE_EXAMPLES, "clutch_reel.py", "batch_parse.py"}
    assert on_disk == covered, (
        f"examples/ and this test have diverged: "
        f"untested={on_disk - covered}, missing={covered - on_disk}"
    )


@pytest.mark.parametrize("name", SIMPLE_EXAMPLES)
def test_example_runs(name: str, demo_path: Path) -> None:
    result = _run(EXAMPLES_DIR / name, str(demo_path))
    assert result.returncode == 0, f"{name} failed:\n{result.stderr}"
    assert result.stdout.strip(), f"{name} printed nothing"


def test_batch_parse_writes_parquet(demo_path: Path, tmp_path: Path) -> None:
    """``batch_parse.py`` takes a directory, so point it at one holding the fixture."""
    pl = pytest.importorskip("polars")

    demos = tmp_path / "demos"
    demos.mkdir()
    # Symlink rather than copy: these files run to hundreds of megabytes.
    (demos / demo_path.name).symlink_to(demo_path.resolve())
    out = tmp_path / "parquet"

    result = _run(
        EXAMPLES_DIR / "batch_parse.py",
        str(demos),
        "--out",
        str(out),
        "--tables",
        "rounds",
        "stats",
    )
    assert result.returncode == 0, f"batch_parse.py failed:\n{result.stderr}"

    for table in ("rounds", "stats"):
        path = out / f"{table}.parquet"
        assert path.is_file(), f"{table}.parquet was not written"
        frame = pl.read_parquet(path)
        assert frame.height > 0
        # Every row is attributable back to its source demo.
        assert frame["demo"].to_list() == [demo_path.stem] * frame.height


def test_clutch_reel_renders(demo_path: Path, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    out = tmp_path / "clutches"

    # One clutch is enough to prove the stats -> snapshots -> plot chain works;
    # rendering all of them would dominate the suite's runtime.
    result = _run(
        EXAMPLES_DIR / "clutch_reel.py",
        str(demo_path),
        "--out",
        str(out),
        "--limit",
        "1",
    )
    if "no clutch" in result.stdout.lower() or "0 clutch situation" in result.stdout:
        pytest.skip("demo has no clutch rounds")
    assert result.returncode == 0, f"clutch_reel.py failed:\n{result.stderr}"
    assert list(out.glob("*.gif")), f"no GIF written:\n{result.stdout}"
