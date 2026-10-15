"""Compare public parser APIs with exact output checks and fresh processes.

Install both parsers in one environment. Run --help for usage. Input files are
read before timing to warm the OS cache. No parser results are preloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

CASES = ("combat", "ticks", "ticks-pawn", "sampled", "seek")
PROPS = ["X", "Y", "Z", "health", "armor", "team_num", "name"]
EVENTS = {
    "kills": (
        "player_death",
        {"user_steamid": "victim_steamid", "assistedflash": "assist_flash"},
        [
            "tick",
            "attacker_steamid",
            "victim_steamid",
            "assister_steamid",
            "weapon",
            "headshot",
            "assist_flash",
        ],
    ),
    "damages": (
        "player_hurt",
        {"user_steamid": "victim_steamid", "health": "health_post", "armor": "armor_post"},
        [
            "tick",
            "attacker_steamid",
            "victim_steamid",
            "weapon",
            "dmg_health",
            "dmg_armor",
            "health_post",
            "armor_post",
        ],
    ),
    "shots": ("weapon_fire", {"user_steamid": "steamid"}, ["tick", "steamid", "weapon"]),
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def schema():
    import polars as pl

    return {
        "tick": pl.Int32,
        "steamid": pl.UInt64,
        "name": pl.String,
        "X": pl.Float32,
        "Y": pl.Float32,
        "Z": pl.Float32,
        "health": pl.Int32,
        "armor": pl.Int32,
        "team_num": pl.UInt32,
    }


def canonical(frames, engine: str, case: str):
    import polars as pl

    if engine == "demoparser2":
        frames = {name: pl.from_pandas(frame) for name, frame in frames.items()}
    if case == "combat":
        result = {}
        for name, (_, rename, columns) in EVENTS.items():
            frame = frames[name]
            if engine == "demoparser2":
                frame = frame.rename(rename)
            types = {
                column: pl.UInt64
                if column.endswith("steamid")
                else pl.String
                if column == "weapon"
                else pl.Boolean
                if column in ("headshot", "assist_flash")
                else pl.Int32
                for column in columns
            }
            result[name] = frame.select(columns).cast(types)
        return result
    frame = frames["states"]
    if engine == "demoparser2":
        frame = frame.rename({"armor_value": "armor"})
    elif case not in ("ticks", "ticks-pawn"):
        frame = frame.rename({"x": "X", "y": "Y", "z": "Z"}).with_columns(
            pl.col("side")
            .replace_strict({"terrorist": 2, "counter-terrorist": 3}, default=None)
            .alias("team_num")
        )
    if case not in ("ticks", "ticks-pawn"):
        frame = frame.filter(pl.col("health") > 0)
    types = schema()
    if case == "ticks-pawn":
        types.pop("name")
    return {"states": frame.select(list(types)).cast(types)}


def query(path: Path, engine: str, case: str, ticks: list[int]):
    if engine == "awpy":
        from awpy import Demo

        demo = Demo(path)
        if case == "combat":
            demo.load(*EVENTS)
            return {name: getattr(demo, name) for name in EVENTS}
        if case in ("ticks", "ticks-pawn"):
            props = [prop for prop in PROPS if prop != "name"] if case == "ticks-pawn" else PROPS
            return {"states": demo.ticks(props)}
        return {"states": demo.snapshots(ticks=ticks)}
    from demoparser2 import DemoParser

    parser = DemoParser(str(path))
    if case == "combat":
        events = dict(parser.parse_events([spec[0] for spec in EVENTS.values()]))
        return {name: events[spec[0]] for name, spec in EVENTS.items()}
    props = [prop for prop in PROPS if prop != "name"]
    props[props.index("armor")] = "armor_value"
    return {"states": parser.parse_ticks(props, ticks=ticks or None)}


def peak_mib() -> float:
    # ru_maxrss can retain the fork parent's pre-exec high-water mark.
    # VmHWM belongs to this executable's address space instead.
    return next(
        int(line.split()[1]) / 1024
        for line in Path("/proc/self/status").read_text().splitlines()
        if line.startswith("VmHWM:")
    )


def worker(args) -> None:
    # Limit CPUs before any native thread pools or parser imports exist.
    os.sched_setaffinity(0, set(args.cpus[: args.worker_threads]))
    os.environ.update(
        RAYON_NUM_THREADS=str(args.worker_threads),
        POLARS_MAX_THREADS=str(args.worker_threads),
        AWPY_TICK_SEGMENTS=str(args.worker_threads),
        OMP_NUM_THREADS=str(args.worker_threads),
        OPENBLAS_NUM_THREADS=str(args.worker_threads),
    )
    import polars  # noqa: F401

    if args.engine == "awpy":
        import awpy  # noqa: F401
    else:
        import demoparser2  # noqa: F401
        import pandas  # noqa: F401
        import pyarrow  # noqa: F401
    # Exclude imports and cold disk reads, but include fresh construction,
    # decoding and each API's native DataFrame materialization.
    digest(args.demo[0])
    baseline = peak_mib()
    cpu = time.process_time()
    start = time.perf_counter()
    frames = query(args.demo[0], args.engine, args.case, args.tick)
    native_end = time.perf_counter()
    frames = canonical(frames, args.engine, args.case)
    finish = time.perf_counter()
    result = {
        "api_seconds": native_end - start,
        "seconds": finish - start,
        "cpu_seconds": time.process_time() - cpu,
        "peak_rss_mib": peak_mib(),
        "baseline_peak_rss_mib": baseline,
        "rows": {name: frame.height for name, frame in frames.items()},
    }
    # IPC and exact comparison are outside the timer and memory observation.
    for name, frame in frames.items():
        frame.write_ipc(args.tables / f"{name}.arrow")
    print(json.dumps(result))


def check_tables(directory: Path, baseline: Path, engine: str, first: bool) -> None:
    import polars as pl
    from polars.testing import assert_frame_equal

    baseline.mkdir(exist_ok=True)
    for path in directory.glob("*.arrow"):
        actual = pl.read_ipc(path)
        if path.stem == "states":
            actual = actual.sort(["tick", "steamid"])
        if first and engine == "awpy":
            actual.write_ipc(baseline / path.name)
        else:
            expected = pl.read_ipc(baseline / path.name)
            assert_frame_equal(actual, expected, check_exact=True)


def run(args) -> None:
    from awpy import Demo

    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("awpy", "demoparser2", "polars", "pandas", "pyarrow")
        },
        "harness_sha256": digest(Path(__file__)),
        "cpus": args.cpus,
        "repeat": args.repeat,
        "warmup_pairs": 1,
        "runs": [],
        "timing": "Warm OS cache; fresh process and parser; imports excluded. "
        "seconds includes conversion to common Polars tables; api_seconds does not.",
    }
    for module in ("awpy._awpy", "demoparser2.demoparser2"):
        filename = importlib.import_module(module).__file__
        assert filename is not None
        path = Path(filename)
        report[module] = {"path": str(path), "sha256": digest(path)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for path in args.demo:
        path = path.resolve(strict=True)
        end = Demo(path).header["playback_ticks"]
        for threads in args.threads:
            for case in args.cases:
                ticks = (
                    []
                    if case in ("ticks", "ticks-pawn", "combat")
                    else list(range(0, end + 1, 64))
                    if case == "sampled"
                    else [end * i // 5 for i in range(1, 5)]
                )
                record: dict[str, Any] = {
                    "demo": path.name,
                    "demo_sha256": digest(path),
                    "bytes": path.stat().st_size,
                    "threads": threads,
                    "case": case,
                    "selected_ticks": len(ticks),
                    "samples": {"awpy": [], "demoparser2": []},
                }
                with tempfile.TemporaryDirectory(prefix="parser-comparison-") as temporary:
                    base = Path(temporary)
                    for iteration in range(-1, args.repeat):
                        engines = ["awpy", "demoparser2"]
                        if iteration >= 0 and iteration % 2:
                            engines.reverse()
                        for engine in engines:
                            tables = base / engine
                            tables.mkdir(exist_ok=True)
                            command = [
                                sys.executable,
                                str(Path(__file__).resolve()),
                                "--worker",
                                "--engine",
                                engine,
                                "--case",
                                case,
                                "--demo",
                                str(path),
                                "--worker-threads",
                                str(threads),
                                "--tables",
                                str(tables),
                                "--cpus",
                                *map(str, args.cpus),
                            ]
                            for tick in ticks:
                                command.extend(("--tick", str(tick)))
                            process = subprocess.run(
                                command, text=True, capture_output=True, timeout=180
                            )
                            if process.returncode:
                                raise RuntimeError(process.stderr or process.stdout)
                            sample = json.loads(process.stdout)
                            check_tables(tables, base / "expected", engine, iteration == -1)
                            if iteration >= 0:
                                record["samples"][engine].append(sample)
                record["exact_output_check"] = "passed for both engines on every run"
                for engine, samples in record["samples"].items():
                    durations = [s["seconds"] for s in samples]
                    record[engine] = {
                        "median_seconds": statistics.median(durations),
                        "min_seconds": min(durations),
                        "max_seconds": max(durations),
                        "median_api_seconds": statistics.median(s["api_seconds"] for s in samples),
                        "median_peak_rss_mib": statistics.median(
                            s["peak_rss_mib"] for s in samples
                        ),
                        "rows": samples[0]["rows"],
                    }
                report["runs"].append(record)
                args.output.write_text(json.dumps(report, indent=2) + "\n")
                print(
                    f"{path.name} {threads} CPU {case}: "
                    f"Awpy {record['awpy']['median_seconds']:.3f}s; "
                    f"demoparser2 {record['demoparser2']['median_seconds']:.3f}s",
                    flush=True,
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--threads", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--cpus", type=int, nargs="+", default=sorted(os.sched_getaffinity(0)))
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--engine", choices=("awpy", "demoparser2"), help=argparse.SUPPRESS)
    parser.add_argument("--case", choices=CASES, help=argparse.SUPPRESS)
    parser.add_argument("--worker-threads", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--tick", action="append", type=int, default=[], help=argparse.SUPPRESS)
    parser.add_argument("--tables", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker and (
        args.output is None
        or args.repeat < 1
        or min(args.threads) < 1
        or max(args.threads) > len(args.cpus)
    ):
        parser.error("--output is required; repeat and CPU counts must be positive and available")
    worker(args) if args.worker else run(args)


if __name__ == "__main__":
    main()
