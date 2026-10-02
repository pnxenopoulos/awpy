# Parsing benchmarks

Run these commands from the repository root. The `parse` target uses
Criterion.rs. It works with both `cargo criterion` and `cargo bench`.

## Select a demo

In Bash or WSL:

```sh
export AWPY_BENCH_DEMO=/absolute/path/to/match.dem
export AWPY_TICK_SEGMENTS=4
```

In PowerShell:

```powershell
$env:AWPY_BENCH_DEMO = 'C:\demos\match.dem'
$env:AWPY_TICK_SEGMENTS = '4'
```

Use a fixed segment count for comparisons. `AWPY_TICK_SEGMENTS` controls parser
parallelism where the API supports it. Set it to `1` to test serial parsing.
Without this variable, Awpy uses the available CPU count.

Relative demo paths are resolved from the repository root with either runner.

If `AWPY_BENCH_DEMO` is not set, the suite uses the smallest `.dem` file in
the repository root or its `demos/` directory. It does not search subdirectories
or download demos. If no file is found, it prints a warning and skips all
measurements. An explicit path that cannot be read or an invalid demo causes
the run to fail. Do not change the file while a benchmark is running.

The benchmark ID includes the file name and byte count. Use the same file
contents for both runs, even if the names and sizes match.

## Run cargo-criterion

Install the runner once:

```sh
cargo install cargo-criterion --version 1.1.0 --locked
```

Run the full suite, or select a group or operation:

```sh
cargo criterion -p awpy --bench parse
cargo criterion -p awpy --bench parse -- 'decode/'
cargo criterion -p awpy --bench parse -- 'datasets/(players|stats)/'
cargo criterion -p awpy --bench parse -- 'datasets/kills_bomb_shots_'
```

The full suite can take several minutes. The default settings are 10 samples,
a 1-second warm-up, and a 10-second target measurement time per benchmark.
Flat sampling keeps the iteration count equal across samples. Slow operations
can exceed the target time to collect all samples.

For a longer run:

```sh
cargo criterion -p awpy --bench parse -- 'datasets/stats/' --sample-size 30 --warm-up-time 3 --measurement-time 30
```

Use history labels to identify revisions. Run the same command after each
change, with a new label:

```sh
cargo criterion -p awpy --bench parse --history-id before -- 'datasets/'
# Apply the change, then run:
cargo criterion -p awpy --bench parse --history-id after -- 'datasets/'
```

Reports are in `target/criterion/reports/`. See the
[cargo-criterion guide](https://github.com/bheisler/cargo-criterion)
for report and history options. Do not run other CPU-intensive work during
measurement.

## Save an explicit baseline with cargo bench

The same target works without the cargo-criterion runner. Use Criterion.rs
baseline options with `cargo bench`, not `cargo criterion`:

```sh
cargo bench -p awpy --bench parse -- --save-baseline before
# Apply the change, then run:
cargo bench -p awpy --bench parse -- --baseline before
```

To test each operation once without statistical measurement:

```sh
cargo bench -p awpy --bench parse -- --test
```

This checks that the operations succeed. It does not compare their outputs
with known correct results. Run the Rust tests and demo fixture tests before
you accept a parser change.

## What the suite measures

| Group / operation | Work |
| --- | --- |
| `init/from_file` | Open the file and create a memory map. Do not decode it. |
| `init/parse_send_tables`, `parse_class_info`, `parse_init` | First call to each public initialization API. Each includes shared playback preparation; these times are not separate pipeline stages. |
| `decode/messages` | List demo commands without entity decode. |
| `decode/events` | Decode all game events on first access. |
| `decode/run_to_end` | Decode all entity classes through the last tick. Count tick callbacks. |
| `decode/player_entities` | Decode only player controllers and pawns. Count tick callbacks. |
| `datasets/players`, `rounds`, `stats` | Build the roster, rounds, or player stats. Stats exclude knife rounds. |
| `datasets/event_datasets` | Collect kills, damages, bomb events, blinds, and shots together. |
| `datasets/kills` | Collect kills only. |
| `datasets/kills_bomb_shots_combined` | Collect three selected datasets in one call. |
| `datasets/kills_bomb_shots_separate` | Collect the same three datasets in separate calls on one parser. |
| `datasets/projectiles` | Collect grenade trajectories, fires, and smokes together. |
| `datasets/snapshots_every_64` | Collect player state every 64 ticks, from tick zero to the end. |

Each iteration uses a fresh parser with empty caches. Except for
`init/from_file`, file opening and memory mapping occur outside the timer.
The parser and returned result are also dropped outside the timer. Temporary
allocations and their cleanup inside each API call are included.

Only one iteration's parser and result are retained at a time. The suite does
not copy the whole demo into a new byte buffer for each iteration.
`black_box` prevents the compiler from removing the measured work.

These are repeated-read benchmarks: the OS can cache file pages. They do not
measure cold disk reads. Throughput uses the complete demo size for one
operation, even if that operation skips data or makes several passes. It is
not a count of physical bytes read.

These benchmarks measure Rust API time. They do not measure Python call
overhead, Polars DataFrame conversion, Python dataset caches, or peak memory.
Use a memory profiler for allocation or resident-memory measurements.

For a valid comparison, keep the demo, Rust toolchain, build settings,
segment count, and machine the same. Keep `target/criterion/` between runs.
Record the demo checksum and the Git revision with the results. Do not
compare these measurements with the old byte-copy benchmark as if their
timing boundaries were the same.
