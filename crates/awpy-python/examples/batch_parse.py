"""Parse a directory of demos into one Parquet dataset per table.

The workflow most analysis actually starts from: turn a folder of ``.dem`` files
into columnar files you can query without re-parsing anything. Each output table
gains a ``demo`` column (the file stem) so rows stay attributable once the matches
are stacked together.

Parsing is the expensive step and it is CPU-bound inside Rust, so demos are
processed one at a time and written incrementally — a failure partway through
leaves the demos already done on disk.

Usage:
    python batch_parse.py demos/ --out parquet/
    python batch_parse.py demos/ --out parquet/ --tables rounds kills stats
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import polars as pl
from awpy import Demo

# Dataset name -> how to pull it off a Demo. All of these are cached properties
# built in one shared pass, so asking for several costs little more than one.
TABLES: dict[str, str] = {
    "rounds": "rounds",
    "kills": "kills",
    "damages": "damages",
    "bomb": "bomb",
    "shots": "shots",
    "grenades": "grenades",
    "stats": "stats",
    "players": "players",
    "round_economy": "round_economy",
}


def parse_one(path: Path, tables: list[str]) -> dict[str, pl.DataFrame]:
    """Every requested table for one demo, tagged with the demo's name."""
    demo = Demo(path)
    out: dict[str, pl.DataFrame] = {}
    for name in tables:
        frame: pl.DataFrame = getattr(demo, TABLES[name])
        # Tag first so the column order is stable across demos.
        out[name] = frame.select(
            pl.lit(path.stem).alias("demo"),
            pl.lit(demo.header["map_name"]).alias("map_name"),
            pl.all(),
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("demos", type=Path, help="directory of .dem files")
    parser.add_argument("--out", type=Path, default=Path("parquet"), help="output directory")
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=sorted(TABLES),
        default=["rounds", "kills", "stats"],
        help="which datasets to export (default: rounds kills stats)",
    )
    args = parser.parse_args()

    paths = sorted(args.demos.glob("*.dem"))
    if not paths:
        raise SystemExit(f"no .dem files in {args.demos}")
    args.out.mkdir(parents=True, exist_ok=True)

    collected: dict[str, list[pl.DataFrame]] = {name: [] for name in args.tables}
    failed: list[tuple[Path, str]] = []

    for i, path in enumerate(paths, 1):
        size_mb = path.stat().st_size / 1e6
        print(f"[{i}/{len(paths)}] {path.name} ({size_mb:.0f} MB)... ", end="", flush=True)
        started = time.monotonic()
        try:
            for name, frame in parse_one(path, args.tables).items():
                collected[name].append(frame)
        except Exception as exc:  # a corrupt or truncated demo shouldn't stop the run
            print(f"FAILED ({exc})")
            failed.append((path, str(exc)))
            continue
        print(f"{time.monotonic() - started:.1f}s")

        # Write after each demo, so an interrupted run still leaves usable output.
        for name, frames in collected.items():
            if frames:
                pl.concat(frames, how="diagonal_relaxed").write_parquet(
                    args.out / f"{name}.parquet"
                )

    print(f"\nWrote {len(args.tables)} table(s) to {args.out}/")
    for name, frames in collected.items():
        if frames:
            rows = sum(f.height for f in frames)
            print(f"  {name}.parquet  {rows:,} rows from {len(frames)} demo(s)")

    if failed:
        print(f"\n{len(failed)} demo(s) failed:")
        for path, error in failed:
            print(f"  {path.name}: {error}")

    print("\nQuery it without re-parsing:")
    print(f'  pl.scan_parquet("{args.out}/kills.parquet").group_by("demo").len().collect()')


if __name__ == "__main__":
    main()
