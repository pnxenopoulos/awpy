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

# Names and combat parsing — 2026-10-14

Local measurements on a Ryzen 7 7800X3D under WSL2, Rust 1.96.1,
Python 3.14.6, and Polars 2.0.0. Both builds use release settings and pbdems2
0.4.0. One or four physical cores are fixed by CPU affinity. Each case has one
warmup and seven fresh-process samples in alternating build order. The input
file cache is warm. No builds or tests ran during timing.

## Implemented in Awpy

The Python API timings include construction and complete table creation.
Imports, output serialization, and exact comparisons are outside the timer.
Every returned column and value matched the original build on both FURIA demos.

| Demo | Cores | Case | Before (s) | After (s) |
| --- | ---: | --- | ---: | ---: |
| Ancient | 1 | `ticks` | 1.617 | 1.670 |
| Ancient | 1 | `ticks/names` | 1.690 | 1.711 |
| Ancient | 1 | `load/combat` | 1.255 | 1.248 |
| Ancient | 4 | `ticks` | 0.649 | 0.623 |
| Ancient | 4 | `ticks/names` | 1.698 | 0.699 |
| Ancient | 4 | `load/combat` | 1.247 | 0.503 |
| Mirage | 1 | `ticks` | 1.588 | 1.580 |
| Mirage | 1 | `ticks/names` | 1.697 | 1.687 |
| Mirage | 1 | `load/combat` | 1.215 | 1.226 |
| Mirage | 4 | `ticks` | 0.660 | 0.653 |
| Mirage | 4 | `ticks/names` | 1.722 | 0.703 |
| Mirage | 4 | `load/combat` | 1.248 | 0.505 |

`ticks/names` requests the default six properties plus `name`. `load/combat`
returns kills, damages, shots, blinds, and bomb events. Four-core named ticks
are about 2.4 times faster; combat is about 2.5 times faster. Four-core ticks
without names also improved slightly. Single-core controls show no consistent
gain: Ancient ticks rose 3.3%, while Mirage ticks fell 0.5%; individual samples
vary more than these differences. These controls do not establish zero overhead.
A separate 15-sample single-core repeat measured Ancient at 1.586 → 1.602 s (+1.0%) and
Mirage at 1.571 → 1.574 s (+0.2%). No material single-core change is established.

Names are read from recorded controller state at each tick. Validated original
controller handles identify dead pawns after a cold keyframe. No final-roster
join is used. Other controller-only properties remain serial.

Combat workers restore string-table updates and descriptors recorded after
signon. A metadata scan skips entity payloads and retains event source order,
including events before a full packet on the same tick. Workers merge flash
history by full pawn identity. Trades are classified after the ordered merge.
A post-signon class-schema change retains the serial path. Stats with round
and roster reconstruction remain serial.

Exact named-tick comparisons also passed on Nuke, Vertigo, Overpass part 1,
and Ancient part 2. Complete serial-versus-parallel combat comparisons passed
on recordings with late weapon/bomb baselines and same-tick keyframe events.
Small synthetic tests cover those cases without large new fixtures.

## Validation

- Python release-wheel suite: 458 passed, one expected skip.
- Rust workspace and binding unit tests: 183 passed, three existing asset tests ignored.
- Seven Rust doctests passed.
- Workspace Clippy with warnings denied, CI Ruff scopes, and ty on `python` passed.
- Sphinx built the documentation with warnings treated as errors.

## Isolated pbdems2 property-filter investigation

The prototype is under ignored `target/parsing-optimization/`, outside the
pbdems2 source tree. It skips unrequested scalar values using the existing
decoder skip path. Pointer and dynamic-array shape updates remain decoded.
The combat dependency plan is resolved from each demo's serializers.

These are native five-dataset timings from the same executable with filtering
off or on. Parser construction, dependency-plan compilation, and JSON output
are excluded. They are not Python API timings. Every combat field matched on
every run. The prototype uses a process-wide plan only to run this experiment.

| Demo | Cores | Full (s) | Projected (s) | Time reduction |
| --- | ---: | ---: | ---: | ---: |
| Ancient | 1 | 1.235 | 1.111 | 10.1% |
| Ancient | 4 | 0.496 | 0.472 | 4.9% |
| Mirage | 1 | 1.212 | 1.081 | 10.8% |
| Mirage | 4 | 0.501 | 0.465 | 7.3% |
| Nuke | 1 | 0.981 | 0.892 | 9.1% |
| Nuke | 4 | 0.436 | 0.408 | 6.5% |
| Ancient part 2 | 1 | 0.649 | 0.606 | 6.7% |
| Ancient part 2 | 4 | 0.307 | 0.290 | 5.5% |

The gain is about 5–11%. Four-core peak RSS fell by about 4–6 MiB. RSS includes
mapped input and retained allocations; it does not measure entity storage alone.

The upstream touch points are `Entity::apply_update`, `BaselineCache::apply`,
and the packet-entity dispatch and prepared-session APIs in `playback.rs` and
`playback/prepared.rs`. The prototype leaves the existing field-map reserve
unchanged; a compiled plan could size it from the retained fields.

A production design needs:

- An immutable field plan per playback session, compiled for its serializers.
- Dataset dependencies for identity, coordinates, weapon state, and nested fields.
- Pointer/array dependencies and wildcard selection for dynamic descendants.
- The same plan during baseline decode, updates, seeks, and parallel segments.
- Separate cached state for each plan and schema; widening a plan needs replay.
- Unchanged full decoding by default, with decode/skip validation parity tests.

Boon needs its own dependency audit and replay checks before it uses this API.
Its modifier and ability arrays cannot use the small CS2 combat plan. No public
pbdems2 API, dependency version, or production decoder was changed.

Raw samples, source backups, probe code, and saved wheels remain in the local
ignored `target/parsing-optimization/` directory. They must not be committed.
See [README.md](README.md) for the benchmark commands.

# Property filtering — 2026-10-15

Local release-build measurements on the same Ryzen 7 7800X3D under WSL2,
Rust 1.96.1, Python 3.14.6, and Polars 2.0.0. The baseline includes the names
and parallel combat changes above, with pbdems2 0.4.0. The candidate uses the
production property-filter API in pbdems2 0.4.1. Dependencies and CPU affinity
match. No builds or tests ran during timing.

## Python API

Each case has one warmup and seven fresh-process samples in alternating build
order. Input is cached. Timers include construction and complete table creation;
imports, IPC output, and exact comparisons are excluded. Values below are medians.

| Demo | Cores | Case | Before (s) | After (s) |
| --- | ---: | --- | ---: | ---: |
| Ancient | 1 | `ticks` | 1.593 | 1.592 |
| Ancient | 1 | `ticks/names` | 1.688 | 1.690 |
| Ancient | 1 | `load/combat` | 1.240 | 1.128 |
| Ancient | 4 | `ticks` | 0.645 | 0.634 |
| Ancient | 4 | `ticks/names` | 0.699 | 0.655 |
| Ancient | 4 | `load/combat` | 0.498 | 0.475 |
| Mirage | 1 | `ticks` | 1.572 | 1.567 |
| Mirage | 1 | `ticks/names` | 1.694 | 1.681 |
| Mirage | 1 | `load/combat` | 1.221 | 1.105 |
| Mirage | 4 | `ticks` | 0.653 | 0.657 |
| Mirage | 4 | `ticks/names` | 0.711 | 0.699 |
| Mirage | 4 | `load/combat` | 0.509 | 0.475 |

Combat parsing is 9.1–9.5% faster on one core and 4.6–6.7% faster on four.
Tick queries do not use property filtering. Their changes vary between repeats;
these controls show no material regression. A prior 15-sample four-core control
repeat measured named ticks at 0.669 → 0.670 s on Ancient and 0.677 → 0.685 s
on Mirage. The final seven-sample differences do not establish a name-query gain.

All returned columns and values match the baseline. Tick rows are sorted by
`tick` and `steamid` before comparison because worker merge order can vary.
Combat row order is compared directly. Complete combat comparisons also pass on
Nuke, Vertigo, Ancient part 2, Fnatic–MIBR Mirage, and Overpass part 1.

## Implementation and full-decoding controls

Awpy compiles one immutable dependency filter per combat request and shares it
between workers. Round and roster collection retain full fields. Files with
later schema commands use full decoding. No Python API or dataset schema changed.

pbdems2 resolves requested fields and nested subtrees against the session schema.
Initial state, baselines, deltas, seeks, segments, and checkpoints use the same
selection. Pointer presence and array lengths remain decoded. A different schema
or an attempt to widen existing filtered state is rejected. Skipped values still
consume their wire data and enforce limits.

Full decoding has a separate specialized field loop. Saved before/after native
binaries used the same bench profile and CPU 2, with 50 Criterion samples,
0.5-second warmup, 1.5-second measurement, and alternating order. Full-update and
create controls range from 1.6% faster to 0.6% slower. The initially noisy small
create case settled at 167.975 → 168.628 µs (+0.4%) over eight runs per build.
These results show no material full-decoding regression, not proof of zero cost.
Selecting two of 30 mixed fields reduces synthetic update time by 24–26%.

An early candidate slowed the full field loop by 6–7%. It was rejected. Keeping
filter compilation out of the public generic constructor and separating the
projected insertion form restored the full loop's code generation. String skip
limits retain fast paths for empty strings and packets below the limit.

## Boon and validation

An isolated copy of Boon used the same API on `108575009.dem` and
`111155916.dem`. Health, max health, and the nested ability array matched exactly
every 64 ticks: 1,938,183 field values. Filtered and unfiltered direct seeks
also match at ticks 187554 and 40441. Boon's production source is unchanged;
its datasets need their own input selections before adopting filtering.

- pbdems2 workspace tests and doctests pass. Regression cases cover baselines,
  array changes, pointer clearing, slot reuse, schema changes, seek/segment
  replay, checkpoints, concurrent filters, truncated input, and decode limits.
- Awpy: 164 Rust tests and seven doctests pass; three existing asset tests remain
  ignored. The release-wheel Python suite has 458 passes and one expected skip.
- All 256 pbdems2 benchmark smoke cases pass.
- Clippy, Rust formatting, Ruff, ty, and Sphinx with warnings as errors pass.

Local builds use a command-scoped patch to the pbdems2 checkout. Publish 0.4.1,
then run `cargo update -p pbdems2` in Awpy without that patch to record the registry
source and checksum before CI or release. No permanent path override was added.

Raw reports, exact-output files, source backups, probes, and wheels remain under
ignored `target/property-filter/`. They must not be committed.

## Updated comparison with demoparser2

The final Awpy build and demoparser2 0.42.0 use the same Python environment,
four fixed physical cores, and seven fresh-process samples per case. Each pair
alternates parser order after one warmup. Input is cached; imports and exact
checks are excluded. Times include construction, native table creation, and
conversion to the common Polars schema. Every common column and value matches.

| Demo | Task | Awpy (s) | demoparser2 (s) | Awpy speedup |
| --- | --- | ---: | ---: | ---: |
| Ancient | Kills, damages, shots | 0.483 | 0.593 | 1.23× |
| Ancient | All ticks with names | 0.739 | 1.070 | 1.45× |
| Ancient | All ticks without names | 0.661 | 1.032 | 1.56× |
| Ancient | Alive players every 64 ticks | 0.379 | 0.577 | 1.52× |
| Ancient | Alive players at four ticks | 0.079 | 0.551 | 7.02× |
| Mirage | Kills, damages, shots | 0.475 | 0.565 | 1.19× |
| Mirage | All ticks with names | 0.710 | 0.994 | 1.40× |
| Mirage | All ticks without names | 0.665 | 0.964 | 1.45× |
| Mirage | Alive players every 64 ticks | 0.372 | 0.573 | 1.54× |
| Mirage | Alive players at four ticks | 0.056 | 0.570 | 10.19× |

These are public API tasks, not isolated decoder timings. Awpy also computes
extra event fields and snapshot state that the common output discards.
Combat positions are excluded from equality checks because the APIs can sample
different event-time states. Full tick queries include dead players; sparse
queries include only alive players. No universal parser-speed claim follows
from these two demos.
