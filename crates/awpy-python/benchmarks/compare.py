"""Compare benchmark reports, refusing changed outputs or measurement settings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def indexed(report: dict) -> dict:
    result = {}
    for run in report["runs"]:
        key = (run["demo"]["sha256"], run["case"])
        if key in result:
            raise ValueError(f"duplicate result: {key}")
        result[key] = run
    return result


def compare(baseline: dict, candidate: dict, allow_config_change: bool = False) -> list[dict]:
    left, right = indexed(baseline), indexed(candidate)
    if left.keys() != right.keys():
        raise ValueError("reports must cover the same demo contents and cases")
    if baseline["harness_sha256"] != candidate["harness_sha256"]:
        raise ValueError("benchmark harness differs; measure both builds with the same harness")
    if not allow_config_change:
        for field in ("build_profile", "repeat", "warmup"):
            if baseline[field] != candidate[field]:
                raise ValueError(f"measurement setting differs: {field}")
    rows = []
    for key, before in left.items():
        after = right[key]
        label = f"{before['demo']['name']}:{before['case']}"
        if before["status"] == after["status"] == "skipped":
            continue
        if before["status"] != "ok" or after["status"] != "ok":
            raise ValueError(f"{label}: failed or unmatched skipped case")
        if before["output"] != after["output"]:
            raise ValueError(f"{label}: output fingerprint changed")
        if not allow_config_change:
            for field in (
                "python",
                "polars",
                "platform",
                "machine",
                "processor",
                "host",
                "cpu_count",
                "threads",
            ):
                if before["environment"][field] != after["environment"][field]:
                    raise ValueError(f"{label}: environment differs: {field}")
        old, new = before["median_seconds"], after["median_seconds"]
        rows.append(
            {
                "case": label,
                "baseline_seconds": old,
                "candidate_seconds": new,
                "change_percent": (new / old - 1) * 100 if old else None,
                "baseline_peak_rss_bytes": before["process_peak_rss_bytes"],
                "candidate_peak_rss_bytes": after["process_peak_rss_bytes"],
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--allow-config-change",
        action="store_true",
        help="allow deliberate thread/profile experiments; output checks still apply",
    )
    args = parser.parse_args()
    try:
        rows = compare(
            json.loads(args.baseline.read_text()),
            json.loads(args.candidate.read_text()),
            args.allow_config_change,
        )
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"error: {error}\n")
    print(f"{'demo:case':55} {'before (s)':>12} {'after (s)':>12} {'change':>10}")
    for row in rows:
        change = f"{row['change_percent']:+.1f}%" if row["change_percent"] is not None else "n/a"
        print(
            f"{row['case']:55} {row['baseline_seconds']:12.6f} "
            f"{row['candidate_seconds']:12.6f} {change:>10}"
        )
    print("Negative change means faster. Inspect samples and repeat alternating runs.")


if __name__ == "__main__":
    main()
