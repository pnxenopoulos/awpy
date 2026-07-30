"""Who trades for whom, from the kills dataset's trade flags.

A *trade* is a kill that avenges a teammate killed moments earlier (within 5
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
from pathlib import Path

import polars as pl
from awpy import Demo

TRADE_WINDOW_SECONDS = 5.0


def trade_pairs(demo: Demo) -> pl.DataFrame:
    """Match each trade kill to the teammate's death it avenged.

    A trade kill avenges the most recent death that (a) is flagged
    ``victim_traded``, (b) was inflicted by the player this kill just killed, and
    (c) happened within the trade window. Rebuilding the link this way — rather
    than trusting adjacency — keeps it correct when several players die at once.
    """
    kills = demo.kills.sort("tick")
    window = int(TRADE_WINDOW_SECONDS * demo.tick_rate)

    avenged = kills.filter(pl.col("victim_traded")).select(
        died_tick="tick",
        avenged_name="victim_name",
        # The player who got this kill is the one a teammate then traded.
        killer="attacker_steamid",
    )
    revenge = kills.filter(pl.col("is_trade")).select(
        "tick",
        trader_name="attacker_name",
        # This kill's victim is the killer being punished.
        killer="victim_steamid",
    )

    # Join on the punished killer, then keep the closest preceding death.
    return (
        revenge.join(avenged, on="killer", how="inner")
        .filter(
            (pl.col("died_tick") < pl.col("tick"))
            & (pl.col("tick") - pl.col("died_tick") <= window)
        )
        .sort("tick", "died_tick")
        .group_by("tick", "trader_name", maintain_order=True)
        .last()
        .select("tick", "trader_name", "avenged_name")
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
    print("  (one kill can avenge several teammates, so these differ)")

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
