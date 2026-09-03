"""Benchmark how long awpy takes to parse a CS2 demo.

Parsing is **lazy**: ``Demo(path)`` only opens and verifies the file (near
instant), and each dataset (``kills``, ``ticks``, ...) is parsed on first access
and cached. There is no single "parse the demo" step — the cost lives in the
dataset passes, and each pass scans the demo independently. So this benchmark
reports, per demo:

* ``construct`` — ``Demo(path)`` (repeated; this is the cheap, lazy step);
* one row per dataset — a **cold** parse (fresh ``Demo`` each, so nothing is
  reused), with wall time, row count, and throughput (MB/s of demo scanned);
* a total for the measured set — roughly what a "give me everything" extraction
  costs, since the passes don't share work.

Demos come from the same place the tests use — the ``awpy-fixtures`` manifest,
cached under ``~/.cache/awpy-fixtures`` (see ``tests/fixture_store.py``). By
default it benchmarks whatever demos are already cached; nothing is downloaded
unless you ask.

Usage::

    # whatever is cached already (add datasets / repeats as needed)
    python benchmarks/bench_parse.py

    # specific files, every dataset, JSON for tracking over time
    python benchmarks/bench_parse.py --demo a.dem --demo b.dem --all --json out.json

    # let it fetch the smallest fixture if nothing is cached
    AWPY_RUN_FIXTURES=1 python benchmarks/bench_parse.py --download
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from awpy import Demo

# fixture_store lives with the tests; reuse it so demos resolve identically.
_TESTS = Path(__file__).resolve().parent.parent / "tests"
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))

from fixture_store import cache_dir, download_enabled, ensure_demo, load_manifest  # noqa: E402

#: Dataset name -> how to realize it from a Demo. Callables force the parse
#: (and return something with a row count) so we time the whole pass.
DATASETS: dict[str, Callable[[Demo], Any]] = {
    "events": lambda d: d.events.names,
    "rounds": lambda d: d.rounds,
    "kills": lambda d: d.kills,
    "damages": lambda d: d.damages,
    "bomb": lambda d: d.bomb,
    "grenades": lambda d: d.grenades,
    "fires": lambda d: d.fires,
    "smokes": lambda d: d.smokes,
    "shots": lambda d: d.shots,
    "blinds": lambda d: d.blinds,
    "chat": lambda d: d.chat,
    "item_events": lambda d: d.item_events,
    "players": lambda d: d.players,
    "stats": lambda d: d.stats,
    "player_stats": lambda d: d.player_stats(),
    "load_players_stats": lambda d: (d.load("players", "stats"), d.stats)[1],
    "load_events": lambda d: (d.load("kills", "bomb", "shots"), d.shots)[1],
    "load_projectiles": lambda d: (
        d.load("grenades", "fires", "smokes"),
        d.grenades,
    )[1],
    "load_stats_bomb": lambda d: (d.load("stats", "bomb"), d.stats)[1],
    "ticks(xyz)": lambda d: d.ticks(["X", "Y", "Z"], True),
}

#: A representative, reasonably quick default set (the common workflow plus the
#: heavy per-tick sampling). Pass ``--all`` for every dataset above.
DEFAULT_DATASETS = ["events", "kills", "damages", "grenades", "rounds", "ticks(xyz)"]


def _rows(result: Any) -> int | None:
    """Row count of a realized dataset (a DataFrame's height, or a list's len)."""
    height = getattr(result, "height", None)
    if height is not None:
        return int(height)
    if isinstance(result, (list, tuple)):
        return len(result)
    return None


def _warm(path: Path) -> None:
    """Pull the demo through the OS page cache so timings are CPU-bound, not
    a mix of first-touch disk reads and parse."""
    with path.open("rb") as handle:
        while handle.read(1 << 24):
            pass


def bench_construct(path: Path, repeat: int) -> dict[str, float]:
    """Time ``Demo(path)`` — the lazy open+verify step — ``repeat`` times."""
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        Demo(str(path))
        samples.append(time.perf_counter() - start)
    return {"min": min(samples), "median": statistics.median(samples), "repeat": repeat}


#: Below this, a dataset access is a cache hit, not a real parse.
_CACHE_HIT_SECONDS = 1e-3


def _timed(fn: Callable[[], Any], name: str, size_mb: float) -> dict[str, Any]:
    start = time.perf_counter()
    result = fn()
    seconds = time.perf_counter() - start
    cached = seconds < _CACHE_HIT_SECONDS
    return {
        "dataset": name,
        "seconds": seconds,
        "rows": _rows(result),
        "cached": cached,
        "mb_per_s": None if cached else size_mb / seconds,
    }


def bench_sequential(path: Path, datasets: list[str]) -> list[dict[str, Any]]:
    """Time each dataset in order on **one** Demo — the realistic workflow.

    The first access pays the shared cost (the event-stream decode); later
    event-based datasets reuse it, so this reflects what "parse a demo and pull
    several tables" actually costs.
    """
    size_mb = path.stat().st_size / 1e6
    demo = Demo(str(path))
    return [_timed(lambda n=name: DATASETS[n](demo), name, size_mb) for name in datasets]


def bench_cold(path: Path, datasets: list[str]) -> list[dict[str, Any]]:
    """Time each dataset on its own fresh Demo — the isolated cold cost, with no
    sharing between datasets."""
    size_mb = path.stat().st_size / 1e6
    return [_timed(lambda n=name: DATASETS[n](Demo(str(path))), name, size_mb) for name in datasets]


def benchmark_demo(
    path: Path, datasets: list[str], construct_repeat: int, cold: bool
) -> dict[str, Any]:
    """Full benchmark for one demo: construction + dataset parses."""
    size = path.stat().st_size
    _warm(path)
    demo = Demo(str(path))
    header = demo.header
    construct = bench_construct(path, construct_repeat)
    results = bench_cold(path, datasets) if cold else bench_sequential(path, datasets)
    return {
        "name": path.stem,
        "size_bytes": size,
        "map": header.get("map_name"),
        "playback_ticks": header.get("playback_ticks"),
        "mode": "cold (fresh Demo each)" if cold else "sequential (one Demo)",
        "construct": construct,
        "datasets": results,
    }


def discover_demos(explicit: list[str], download: bool) -> list[Path]:
    """Resolve which demos to benchmark: explicit paths, else cached fixtures,
    else (with ``--download`` and ``AWPY_RUN_FIXTURES``) the smallest fixture."""
    if explicit:
        paths = [Path(p) for p in explicit]
        missing = [p for p in paths if not p.exists()]
        if missing:
            raise SystemExit(f"no such demo(s): {', '.join(map(str, missing))}")
        return paths

    cached = sorted(cache_dir().glob("*.dem")) if cache_dir().is_dir() else []
    if cached:
        return cached

    if download and download_enabled():
        manifest = load_manifest()
        if manifest:
            smallest = min(manifest, key=lambda f: f.get("size", float("inf")))
            path = ensure_demo(smallest)
            if path is not None:
                return [path]
    raise SystemExit(
        "no demos found. Pass --demo PATH, or cache a fixture "
        "(AWPY_RUN_FIXTURES=1 python benchmarks/bench_parse.py --download)."
    )


def _print_report(runs: list[dict[str, Any]]) -> None:
    """Human-readable table, one block per demo."""
    for run in runs:
        size_mb = run["size_bytes"] / 1e6
        print(f"\n{run['name']}  ({run['map']}, {size_mb:.0f} MB, {run['playback_ticks']} ticks)")
        print(f"  mode: {run['mode']}")
        c = run["construct"]
        print(f"  {'construct':14} {c['min'] * 1e3:8.1f} ms   (min of {c['repeat']}, lazy)")
        print(f"  {'dataset':14} {'time':>10}  {'rows':>10}   {'MB/s':>6}")
        print(f"  {'-' * 14} {'-' * 10}  {'-' * 10}   {'-' * 6}")
        total = 0.0
        for d in run["datasets"]:
            total += d["seconds"]
            rows = "-" if d["rows"] is None else f"{d['rows']:,}"
            if d.get("cached"):
                time_str, mbps = "  cached", "-"
            else:
                time_str, mbps = f"{d['seconds']:8.3f}s", f"{d['mb_per_s']:.1f}"
            print(f"  {d['dataset']:14} {time_str:>10}  {rows:>10}   {mbps:>6}")
        print(f"  {'-' * 14} {'-' * 10}")
        print(f"  {'total':14} {total:9.3f}s   (sum of {len(run['datasets'])} datasets)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--demo", action="append", default=[], help="demo path (repeatable); default: cached"
    )
    parser.add_argument("--datasets", help="comma-separated dataset names (default: a subset)")
    parser.add_argument("--all", action="store_true", help="benchmark every dataset")
    parser.add_argument(
        "--construct-repeat", type=int, default=5, help="times to repeat Demo(path) (default: 5)"
    )
    parser.add_argument(
        "--cold", action="store_true", help="parse each dataset on its own fresh Demo"
    )
    parser.add_argument(
        "--download", action="store_true", help="fetch the smallest fixture if nothing is cached"
    )
    parser.add_argument("--json", help="also write raw results to this JSON path")
    args = parser.parse_args(argv)

    if args.all:
        datasets = list(DATASETS)
    elif args.datasets:
        datasets = [name.strip() for name in args.datasets.split(",")]
        unknown = [name for name in datasets if name not in DATASETS]
        if unknown:
            known = ", ".join(DATASETS)
            raise SystemExit(f"unknown dataset(s): {', '.join(unknown)}. Known: {known}")
    else:
        datasets = DEFAULT_DATASETS

    demos = discover_demos(args.demo, args.download)
    print(
        f"awpy parse benchmark — {platform.python_implementation()} {platform.python_version()} "
        f"on {platform.system()} {platform.machine()}"
    )
    print(f"{len(demos)} demo(s), datasets: {', '.join(datasets)}")

    runs = [benchmark_demo(path, datasets, args.construct_repeat, args.cold) for path in demos]
    _print_report(runs)

    if args.json:
        payload = {
            "platform": {
                "python": platform.python_version(),
                "system": platform.system(),
                "machine": platform.machine(),
            },
            "runs": runs,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
