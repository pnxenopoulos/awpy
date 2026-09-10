"""Win rate by buy type — does forcing actually work?

Joins ``demo.round_economy`` (each team's equipment value at freeze end, and its
buy classification) to ``demo.rounds`` (who won) to answer the question every
analyst asks first: how often does each kind of buy convert into a round?

One match is far too small a sample to conclude anything — the point here is the
join, which is the reusable part. Run it over a directory of demos (see
``batch_parse.py``) before believing any of the numbers.

Usage:
    python economy.py match.dem
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl
from awpy import Demo

# Cheapest to richest, so the output reads in a sensible order rather than
# alphabetically.
BUY_ORDER = ["pistol", "eco", "force", "full"]


def rounds_with_economy(demo: Demo) -> pl.DataFrame:
    """One row per (round, side) with that team's buy and whether they won it."""
    rounds = demo.rounds.filter(~pl.col("is_knife_round")).select("round_num", "winner_side")
    return (
        demo.round_economy.join(rounds, on="round_num", how="inner")
        .with_columns(won=pl.col("side") == pl.col("winner_side"))
        .with_columns(
            # Sort key for the buy-type ordering above; unknown types sort last.
            buy_rank=pl.col("buy_type").replace_strict(
                {name: i for i, name in enumerate(BUY_ORDER)}, default=len(BUY_ORDER)
            )
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("demo", type=Path, help="path to a .dem file")
    args = parser.parse_args()

    demo = Demo(args.demo)
    economy = rounds_with_economy(demo)

    print(f"{demo.header['map_name']}: {economy['round_num'].n_unique()} rounds\n")

    print("Win rate by buy type")
    print("-" * 52)
    print(f"{'buy':<10} {'rounds':>7} {'won':>5} {'win%':>7} {'avg $':>9}")
    by_buy = (
        economy.group_by("buy_type", "buy_rank")
        .agg(
            rounds=pl.len(),
            won=pl.col("won").sum(),
            equipment=pl.col("equipment_value").mean(),
        )
        .sort("buy_rank")
    )
    for row in by_buy.iter_rows(named=True):
        rate = row["won"] / row["rounds"]
        print(
            f"{row['buy_type']:<10} {row['rounds']:>7} {row['won']:>5} "
            f"{rate:>6.0%} {row['equipment']:>9,.0f}"
        )

    print("\nWin rate by buy type and side")
    print("-" * 52)
    print(f"{'buy':<10} {'side':<18} {'rounds':>7} {'won':>5} {'win%':>7}")
    by_side = (
        economy.group_by("buy_type", "buy_rank", "side")
        .agg(rounds=pl.len(), won=pl.col("won").sum())
        .sort("buy_rank", "side")
    )
    for row in by_side.iter_rows(named=True):
        rate = row["won"] / row["rounds"]
        print(
            f"{row['buy_type']:<10} {row['side']:<18} "
            f"{row['rounds']:>7} {row['won']:>5} {rate:>6.0%}"
        )

    # Eco rounds a team somehow won are worth watching back.
    upsets = economy.filter(pl.col("won") & pl.col("buy_type").is_in(["eco", "pistol"]))
    if upsets.height:
        print("\nRounds won on a pistol/eco buy: ", end="")
        print(", ".join(str(n) for n in sorted(upsets["round_num"].to_list())))


if __name__ == "__main__":
    main()
