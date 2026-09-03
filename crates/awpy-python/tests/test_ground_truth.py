"""Validate Awpy's output against the known scoreboards of real matches.

For every fixture in ``fixtures/manifest.json`` and every stat the manifest
records for a player, this asserts Awpy's parsed value against the real result
(from csstats / FACEIT / HLTV). It is built to grow in two directions without
touching any plumbing:

* **Add a demo** — add an entry to ``awpy-fixtures/manifest.json`` (then re-sync
  the vendored copy, see :mod:`fixture_store`). It is discovered and
  parametrized automatically.
* **Check a new stat** — add the expected value to a player in the manifest and
  register how to read it from a ``Demo`` in :data:`CHECKS`. An unrecognized
  stat key *skips* with a message rather than failing, so the manifest can lead
  the code.

These tests are marked ``fixtures`` and only download demos when
``AWPY_RUN_FIXTURES`` is set (otherwise they skip). Run the suite with::

    AWPY_RUN_FIXTURES=1 pytest -m fixtures
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import polars as pl
import pytest
from awpy import Demo
from fixture_store import get_demo, load_manifest


@dataclass(frozen=True)
class Check:
    """How to read one ground-truth stat from a ``Demo`` and compare it.

    ``extract`` maps ``(demo, player_name)`` to the parsed value; ``tol`` is the
    allowed absolute difference (``0`` means an exact match).
    """

    extract: Callable[[Demo, str], float | int | None]
    tol: float = 0.0


def _stats_row(demo: Demo, name: str) -> dict | None:
    """The ``demo.stats`` row for ``name`` (matched by display name), or ``None``."""
    rows = demo.stats.filter(pl.col("name") == name).to_dicts()
    return rows[0] if rows else None


def _col(column: str, tol: float = 0.0) -> Check:
    """A check that reads a single ``demo.stats`` column."""

    def extract(demo: Demo, name: str) -> float | int | None:
        row = _stats_row(demo, name)
        return None if row is None else row.get(column)

    return Check(extract, tol)


def _multikill_rounds(demo: Demo, name: str) -> int | None:
    """Rounds with two or more kills (sum of the ``multikill_Nk`` columns)."""
    row = _stats_row(demo, name)
    if row is None:
        return None
    return sum(row[f"multikill_{n}k"] for n in (2, 3, 4, 5))


def _enemies_flashed(demo: Demo, name: str) -> int:
    """Number of enemies this player blinded (from ``demo.blinds``)."""
    return demo.blinds.filter(
        (pl.col("attacker_name") == name) & (pl.col("attacker_side") != pl.col("victim_side"))
    ).height


def _kill_assists(demo: Demo, name: str) -> int | None:
    """Kill assists only (Awpy's ``assists`` includes flash assists as a subset).

    Scoreboard sources put flash assists in a separate column, so their
    "assists" is Awpy's ``assists - flash_assists``.
    """
    row = _stats_row(demo, name)
    return None if row is None else row["assists"] - row["flash_assists"]


# The extension point for "check a new stat": map a manifest ground-truth key to
# how it is read from a Demo (and its comparison tolerance). Keys with no entry
# here are skipped, so the manifest can document a stat before a check exists.
CHECKS: dict[str, Check] = {
    # Objective counts — must match exactly.
    "kills": _col("kills"),
    "deaths": _col("deaths"),
    "assists": Check(_kill_assists),  # scoreboard "assists" = kill assists (no flash)
    "headshots": _col("headshot_kills"),
    "flash_assists": _col("flash_assists"),
    "multikill_rounds": Check(_multikill_rounds),
    # "Enemies flashed" is counted differently across sources (per-blind vs per
    # flash vs deduped per round), so allow +/-1 rather than an exact count.
    "enemies_flashed": Check(_enemies_flashed, tol=1),
    # Derived rates — third-party sources round / define these differently, so
    # allow some slack. Tighten (or fix Awpy) as real divergences are observed.
    # ADR: the systematic overkill over-count is fixed (killing blows capped at
    # the victim's real HP); a small cross-source residual remains (~3 HP/round
    # on one player) — revisit if the full fixture run shows it is a pattern.
    "adr": _col("adr", tol=5.0),
    "kast": _col("kast", tol=3.0),
    "hs_pct": _col("headshot_pct", tol=2.0),
}


def _cases() -> list:
    """One parametrized case per (fixture, player, documented stat)."""
    cases = []
    for entry in load_manifest():
        for player in entry.get("ground_truth", {}).get("players", []):
            for stat, expected in player.items():
                if stat == "name":
                    continue
                cases.append(
                    pytest.param(
                        entry,
                        player["name"],
                        stat,
                        expected,
                        id=f"{entry['name']}::{player['name']}::{stat}",
                    )
                )
    return cases


@pytest.mark.fixtures
@pytest.mark.parametrize("entry, player, stat, expected", _cases())
def test_ground_truth(entry: dict, player: str, stat: str, expected: float) -> None:
    demo = get_demo(entry)
    if demo is None:
        pytest.skip(
            f"fixture '{entry['name']}' unavailable "
            "(set AWPY_RUN_FIXTURES=1 to download, or check connectivity)"
        )
    check = CHECKS.get(stat)
    if check is None:
        pytest.skip(f"no check registered for stat '{stat}' — add one to CHECKS")
    actual = check.extract(demo, player)
    assert actual is not None, f"'{player}' not found in demo.stats (or column missing)"
    if check.tol:
        assert abs(actual - expected) <= check.tol, (
            f"{player} {stat}: got {actual}, expected {expected} (tol +/-{check.tol})"
        )
    else:
        assert actual == expected, f"{player} {stat}: got {actual}, expected {expected}"
