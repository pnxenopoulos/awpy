"""Print a match's rounds and an end-of-match scoreboard.

The "hello world" of demo parsing: what happened each round, and how each player
did over the whole match. Both teams are shown in one table (no side split), the
way a post-match scoreboard reads.

Knife rounds are left out entirely. A knife round is a side-decider played with
melee only; it does not count toward the score, so including it would inflate
kills and skew every per-round average. ``demo.stats`` already excludes them, and
this script drops them from the round table too.

Usage:
    python scoreboard.py match.dem
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl
from awpy import Demo

# (header, stats column). Kept in one place so the header row and the values can
# never fall out of step.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("K", "kills"),
    ("D", "deaths"),
    ("A", "assists"),
    ("HS", "headshot_kills"),
    ("FA", "flash_assists"),
    ("TR", "traded_deaths"),
    ("CL", "clutches_won"),
    ("ADR", "adr"),
    ("KAST", "kast"),
)


def print_rounds(demo: Demo) -> None:
    """One line per round: who won, how, and how long it took."""
    every_round = demo.rounds.sort("round_num")
    rounds = every_round.filter(~pl.col("is_knife_round"))
    skipped = every_round.height - rounds.height

    print(f"\nRounds ({rounds.height})")
    print("-" * 58)
    print(f"{'#':>3}  {'winner':<18} {'reason':<24} {'time':>6}")
    for row in rounds.iter_rows(named=True):
        # Round length in seconds, from the tick rate the demo reports.
        start = row["freeze_end_tick"] or row["start_tick"]
        seconds = (row["end_tick"] - start) / demo.tick_rate if start else 0.0
        print(
            f"{row['round_num']:>3}  {row['winner_side']:<18} "
            f"{row['reason_name']:<24} {seconds:>5.0f}s"
        )
    if skipped:
        print(f"\n({skipped} knife round(s) excluded)")


def print_scoreboard(demo: Demo) -> None:
    """Both teams in one table, sorted by kills."""
    stats = demo.stats
    # Team names come from the roster; tournament servers set them, so this is
    # null on casual matchmaking and the column is simply left out.
    roster = demo.players.select("steamid", "side", "team_clan_name")
    board = stats.join(roster, on="steamid", how="left").sort("kills", descending=True)

    named = board.drop_nulls("team_clan_name").height > 0
    team_width = 10 if named else 0

    print(f"\nScoreboard ({stats['rounds_played'][0]} rounds)")
    print("-" * (26 + team_width + 6 * len(COLUMNS)))
    header = f"{'player':<16}" + (f"{'team':<{team_width}}" if named else "")
    header += "".join(f"{head:>6}" for head, _ in COLUMNS)
    print(header)

    for row in board.iter_rows(named=True):
        line = f"{row['name'][:15]:<16}"
        if named:
            line += f"{(row['team_clan_name'] or '')[:9]:<{team_width}}"
        for _, column in COLUMNS:
            value = row[column]
            # ADR and KAST are rates; everything else is a count.
            line += f"{value:>6.1f}" if isinstance(value, float) else f"{value:>6}"
        print(line)

    print("\nK/D/A=kills/deaths/assists  HS=headshot kills  FA=flash assists")
    print("TR=traded deaths  CL=clutches won  ADR=avg damage/round  KAST=%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("demo", type=Path, help="path to a .dem file")
    args = parser.parse_args()

    demo = Demo(args.demo)
    print(f"{demo.header['map_name']}  ({demo.tick_rate:.0f} tick)")
    print_rounds(demo)
    print_scoreboard(demo)


if __name__ == "__main__":
    main()
