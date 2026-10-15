# Python API benchmarks

Use `bench_api.py` to measure the Python API in isolated processes.
The older `bench_parse.py` script remains available for basic dataset timings.
Use the Rust Criterion suite to separate parser costs from Python API costs.
See [RESULTS.md](RESULTS.md) for local measurements.

## Build and run

Run these commands from `crates/awpy-python`:

```sh
uv sync --locked --no-install-project
uv run --no-sync maturin develop --release --locked
uv run --no-sync python benchmarks/bench_api.py --list
uv run --no-sync python benchmarks/bench_api.py \
  --demo /absolute/path/match.dem --repeat 5 --warmup 1 \
  --threads 4 --segments 4 --output ../../target/benchmarks/before.json
```

Repeat the measurement after the change. Use the same demo contents, cases,
harness, build profile, Python version, and thread limits.

```sh
uv run --no-sync python benchmarks/compare.py \
  ../../target/benchmarks/before.json ../../target/benchmarks/after.json
```

Use repeated `--case` arguments to select workloads. For example:

```sh
uv run --no-sync python benchmarks/bench_api.py \
  --demo /absolute/path/match.dem --case ticks --case ticks/names \
  --case load/combat --threads 4 --segments 4 \
  --output ../../target/benchmarks/parsing.json
```

The harness does not download demos or assets. `--all` includes large full-tick
outputs. Use `--build-profile debug` to label a debug build. This option does not
build the extension. Use `--allow-config-change` in the comparison tool only for
deliberate profile or thread experiments. Output checks remain active.

## Measurement rules

Each demo/case pair runs in a separate process. Each sample creates a new
`Demo`. Only `cached/*` cases load datasets before the timer starts.
Construction is reported separately, except for the `construct` case.
The operating system file cache is warmed before measurement.

Reports include wall and CPU time, output size, process peak RSS, schemas,
null counts, row counts, and value/order fingerprints. They also record demo,
harness, and native-extension hashes. Fingerprints detect drift; they do not
replace exact DataFrame comparisons and fixture tests.

Peak RSS includes imports, mapped input, warmups, output checks, and retained
allocator memory. It is not a count of dataset allocations. RSS is unavailable
on platforms without the supported process resource API.

Run each revision more than once, in alternating order, on an idle machine.
Compare representative demos and both sparse and dense queries. Do not accept
a small difference that is within the sample variation.

## Existing order diagnostic

The harness checks row order as well as values. The current `item_events`
implementation iterates inventory hash sets, so events on the same tick can
change order across runs. `--all` can therefore fail for `dataset/item_events`
on the unchanged parser too. The default case list does not include it.

Keep this diagnostic visible. Use explicit `--case` selections for repeatable
optimization comparisons; do not treat an order failure as a timing result.
See [RESULTS.md](RESULTS.md) for the separate exact-value checks.

CI runs the harness unit tests with the offline pytest selection. CI has no
hardware-dependent timing threshold.

## Compare with demoparser2

Use one Python environment with a release build of Awpy and demoparser2.
The comparison script needs Linux CPU affinity and process resource counters.

```sh
uv pip install demoparser2==0.42.0 pandas pyarrow
uv run --no-sync python benchmarks/bench_demoparser2.py \
  --demo /absolute/path/ancient.dem --demo /absolute/path/mirage.dem \
  --threads 1 4 --repeat 7 --output ../../target/parser-comparison/results.json
```

Cases are grouped combat events, all player ticks with or without names,
alive players every 64 ticks,
and alive players at four exact ticks. Each case returns common Polars columns.
The script checks every row and value on every run. It stops on a mismatch.

Each sample uses a fresh process and parser. The OS file cache is warm. Imports
and output checks are outside the timer. Construction, decoding, native table
creation, and conversion to the common schema are inside the timer. Native API
time is also reported. One pair warms each case; subsequent pairs alternate
parser order. CPU affinity and thread limits apply to both parsers. Use `--cpus`
to select physical cores on the host.

The APIs can do extra work to produce the requested columns. Awpy combat
datasets include positions and trade flags. Its snapshots include inventory
and other state. demoparser2 receives only the requested properties. Thus these
results compare public API tasks, not decoder loops. Event-time positions are
not part of the common combat output because the APIs can sample different
states. The full-tick query includes dead players; sparse queries select only
alive players. Peak RSS includes imports and resident mapped input.

The comparison script's `ticks` case requests names; `ticks-pawn` omits them.
Both retain all player rows, including dead players. Awpy 3.1 supports parallel
decoding for both cases. Other controller-only fields still use serial decoding.
The original Awpy 3.1 baseline used serial decoding for names.
