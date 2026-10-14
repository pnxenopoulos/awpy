"""Who trades for whom, from the kills dataset's trade flags.

A *trade* is a kill that avenges a teammate killed moments earlier (within 5.25
seconds). ``demo.kills`` marks both halves of that exchange:

* ``is_trade`` — this kill **is** the revenge.
* ``victim_traded`` — this kill's victim **was** avenged.

Pairing them up turns a flat kill list into a directed graph: who reliably picks
up refrags for whom, and whose deaths tend to go unanswered. That pairing is the
interesting part, and it is not something any single column gives you.

Usage:
    python trades.py match.dem
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import polars as pl
from awpy import Demo

TRADE_WINDOW_SECONDS = 5.25


def trade_pairs(demo: Demo) -> pl.DataFrame:
    """Pair each trade kill with its earliest eligible, unmatched death."""
    window = round(TRADE_WINDOW_SECONDS * demo.tick_rate)
    pending: dict[int, deque[tuple[int, str | None, str | None]]] = {}
    pairs: list[tuple[int, str | None, str | None]] = []
    for row in demo.kills.sort("tick", maintain_order=True).iter_rows(named=True):
        tick = row["tick"]
        if row["is_trade"] and (queue := pending.get(row["victim_steamid"])):
            while queue and tick - queue[0][0] > window:
                queue.popleft()
            for index, (died_tick, name, side) in enumerate(queue):
                if died_tick < tick and side == row["attacker_side"]:
                    pairs.append((tick, row["attacker_name"], name))
                    del queue[index]
                    break
        if row["victim_traded"]:
            pending.setdefault(row["attacker_steamid"], deque()).append(
                (tick, row["victim_name"], row["victim_side"])
            )
    return pl.DataFrame(
        pairs,
        schema={"tick": pl.Int32, "trader_name": pl.String, "avenged_name": pl.String},
        orient="row",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("demo", type=Path, help="path to a .dem file")
    args = parser.parse_args()

    demo = Demo(args.demo)
    kills = demo.kills

    n_trades = int(kills["is_trade"].sum())
    n_traded = int(kills["victim_traded"].sum())
    print(f"{demo.header['map_name']}: {kills.height} kills")
    print(f"  {n_trades} trade kills avenging {n_traded} deaths")
    print("  (each trade kill avenges one death)")

    # Per player: how often their death gets answered.
    print("\nDeaths avenged")
    print("-" * 44)
    print(f"{'player':<16} {'deaths':>7} {'traded':>7} {'rate':>7}")
    per_victim = (
        kills.group_by("victim_name")
        .agg(deaths=pl.len(), traded=pl.col("victim_traded").sum())
        .with_columns(rate=pl.col("traded") / pl.col("deaths"))
        .sort("rate", descending=True)
    )
    for row in per_victim.iter_rows(named=True):
        name = row["victim_name"] or "<unresolved>"
        print(f"{name[:15]:<16} {row['deaths']:>7} {row['traded']:>7} {row['rate']:>6.0%}")

    # Who does the refragging.
    print("\nTrade kills made")
    print("-" * 28)
    per_trader = (
        kills.filter(pl.col("is_trade"))
        .group_by("attacker_name")
        .len()
        .sort("len", descending=True)
    )
    for row in per_trader.iter_rows(named=True):
        print(f"{(row['attacker_name'] or '?')[:15]:<16} {row['len']:>7}")

    # The graph: trader -> teammate they avenged.
    pairs = trade_pairs(demo)
    print(f"\nTrade pairs ({pairs.height} reconstructed)")
    print("-" * 48)
    top = pairs.group_by("trader_name", "avenged_name").len().sort("len", descending=True).head(15)
    for row in top.iter_rows(named=True):
        print(f"{row['trader_name'][:15]:<16} -> {row['avenged_name'][:15]:<16} {row['len']:>4}")


if __name__ == "__main__":
    main()
