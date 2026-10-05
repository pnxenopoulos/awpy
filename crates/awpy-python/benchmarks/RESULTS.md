# Boon-inspired experiments — 2026-10-04

These are local measurements, not performance guarantees for all demos or hosts.

## Setup

- AMD Ryzen 7 7800X3D, WSL2 Linux, Rust 1.96.1.
- Python 3.13.14, Python Polars 1.42.1, Awpy 3.0.0.
- Release extension with the workspace's LTO settings.
- Four Awpy segments, four Rayon threads, and four Polars threads.
- Five samples after one warmup per case, in isolated processes.
- Warm input file cache. A fresh `Demo` for each sample. Construction is
  measured separately from the selected API call.
- Saved native builds compared sequentially, then in reverse order.
  No builds or tests ran during accepted timing runs.

The starting commit was `4341505`, with local protobuf updates.
Raw reports remain in the local ignored directory
`target/boon-optimization.AXoqUY/`.

## Accepted changes

### Direct seeks for two to four explicit ticks

No window, stride, or event selector can be set for this path.
Larger lists still use the parallel scan. Single-tick behavior is unchanged.

| Demo | Query | Scan | Direct seeks | Time reduction |
| --- | --- | ---: | ---: | ---: |
| Valve Mirage, 84 MB | Two ticks | 95 ms | 35 ms | 64% |
| Valve Mirage, 84 MB | Four ticks | 100 ms | 56 ms | 43% |
| FACEIT Mirage, 438 MB | Two ticks | 435 ms | 52 ms | 88% |
| FACEIT Mirage, 438 MB | Four ticks | 441 ms | 87 ms | 80% |

Source reports: `pbdems-verify.json` and `sparse.json`.
The reverse-order repeat confirmed the gains: 66% / 43% on Valve and
88% / 81% on FACEIT when comparing scan and sparse-only builds.

### Lower-copy snapshot assembly

Plain numeric columns transfer their owned buffers into Polars.
Segment frames are appended as chunks instead of merging all source vectors.
Nullable values, text, Boolean values, schema, and row order stay unchanged.

| Demo | Dense snapshots before | After | Peak RSS before | After |
| --- | ---: | ---: | ---: | ---: |
| Valve Mirage | 361 ms | 282 ms | 611 MiB | 453 MiB |
| FACEIT Mirage | 1,687 ms | 1,246 ms | 2,145 MiB | 1,771 MiB |

Source reports: `sparse.json` and `columns.json`.
The reverse-order repeat measured 384 → 276 ms and 1,692 → 1,249 ms.
Peak RSS was 611 → 452 MiB and 2,136 → 1,734 MiB.
This is a 22–28% time reduction and a 17–26% peak RSS reduction across runs.

An apparent small sampled-query slowdown did not persist in two alternating
15-sample comparisons: 101.2 → 100.2 ms and 99.8 → 100.6 ms.
These differences are too small to claim a sampled-query speed improvement.
Unchanged player, stats, combat, and raw-tick paths served as controls.

RSS includes imports, mapped demo input, output checks, and retained allocator
memory. It is not a count of snapshot allocations.

### pbdems2 0.3.3

The lockfile now selects 0.3.3; the requirement stays `0.3`.
This includes the fixed8 decoder fix. It is a correctness update, not a claimed
speed improvement. An apparent dense-query regression did not persist in
alternating seven-sample comparisons with the saved 0.3.2 build.

### Debug build settings

Kept `opt-level = 1` for the `awpy` and `pbdems2` packages in the dev
profile. Other packages and release settings are unchanged.

| Local build and full Python test suite | Default debug | Targeted opt-level 1 |
| --- | ---: | ---: |
| Rebuild and install | 9.60 s | 11.55 s |
| Tests, including process startup | 332.97 s | 85.63 s |
| Combined | 342.57 s | 97.18 s |

Both runs passed 240 tests with one expected skip. Tests used two pytest
workers, two Awpy segments, and two Polars threads. Each profile rebuilt the
same three packages after a package-scoped debug cleanup; other dependencies
were cached. The one-time cache preparation is excluded from both runs.
This is one local build-and-test comparison, not a cold GitHub runner result.
The compile cost rose by 1.95 s, while the combined time fell by 72%.

## Correctness checks

- Each implementation stage passed the full fixture-enabled Python suite:
  240 passed, with one expected skip for absent clan names.
- Six new sparse-query tests compare exact frames with the scan path across
  three demos and one/four segments. They cover unsorted and duplicate ticks,
  absent ticks, negative ticks, and out-of-range ticks.
- Full dense snapshots from the original 0.3.2 build and the final runtime
  candidate matched exactly: 3,894,070 rows across three demos, all 40 columns,
  including values, row order, dtypes, and nulls.
- All accepted benchmark comparisons matched schemas, null counts, row counts, and
  value/order fingerprints. These hashes supplement exact checks; they do
  not prove equivalence on untested inputs.
- The dependency update passed 116 Rust tests and seven doctests. Three
  existing Rust tests require external geometry/navigation assets and remain
  ignored.

The exact-table checks used Valve `472514809`, FACEIT `6de46e85`, and
HLTV `2394170`, all on Mirage. Wider map/build coverage remains useful.

## Existing item-event order drift

The final all-case smoke test found one existing diagnostic:
`dataset/item_events` changes row order between fresh parses of the same
demo. The original 0.3.2 build has the same behavior. Inventory hash-set
iteration in `Parser::item_events` determines order within each tick.

Four parses per build had identical item-event values after sorting all
columns, and ticks remained sorted before normalization. No item-event code
was changed. The strict harness still reports this order drift as an error;
it does not silently accept it. The other 32 all-case outputs matched,
including row order. These one-sample smoke runs are correctness checks,
not performance evidence.

Final checks also passed: Rust Clippy, rustdoc, Python Ruff and ty, lockfile
validation, two protobuf-generator tests, and the full release Python suite
(240 passed, one expected skip).

## Build identities

The harness SHA-256 was
`d5633e9e45f90b2e4a55f839ec71aff11b210b60f7697fd27a5c83f8500ed449`.

| Saved extension | SHA-256 |
| --- | --- |
| Original, pbdems2 0.3.2 | `aa621ecd4e323b552ad6c1c6f037d2d8fee043902b5488847ba264c478a4a4e2` |
| pbdems2 0.3.3 only | `07e55f60c8d8629eef6464862e578783147930fff51ded3625a6370ed47831c9` |
| Sparse seeks | `bec8c552c757ffe150f798bad633bc32922ffb008dab2afed356352b52cd2482` |
| Sparse seeks and column changes | `511d90041e00bb129d23918a3b9b2a6ec204f4227cd5cfb184d6ba765454b3fb` |

The hashes identify measured binaries, not later documentation-only rebuilds.
One early dependency timing run overlapped test completion. Its report is
named `pbdems-033-discarded-overlap.json`; none of its timings are used here.

See [README.md](README.md) for commands to repeat these measurements.
