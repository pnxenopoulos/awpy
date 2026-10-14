# FAQ

## Which games does Awpy support?

Awpy reads Counter-Strike 2 demos in the [PBDEMS2 format](https://docs.rs/pbdems2/latest/pbdems2/guide/file_structure/index.html).
It does not read CS:GO demos. For Deadlock, use [Boon](https://github.com/pnxenopoulos/boon).

## Which Python versions does Awpy support?

Use Python 3.11–3.15. Awpy requires Polars 2.x.
Wheels are available for Linux, macOS, and Windows.
Installing a wheel does not require Rust. See {doc}`getting-started`.

## How do I get Steam IDs and names?

Use the resolved participants in `demo.kills` and `demo.damages`.
Use `demo.players` for the roster. Raw `demo.events` fields such as
`attacker` contain user IDs, not Steam IDs.

## My demo has no `round_start` / `round_end` events — do rounds still work?

Yes. Awpy reconstructs rounds from the `CCSGameRules` entity.
This includes overtime rounds and does not require round events.

## What are the `winner` numbers?

`2` means terrorist. `3` means counter-terrorist.
Use `winner_side` for the name. Sides change at halftime; a side is not a team identity.

## Why is demo.chat empty?

Awpy can only return chat messages recorded in the demo.
If it finds no supported messages, `demo.chat` returns an empty DataFrame
with the chat schema. See {doc}`datasets`.

## When do map assets download, and can I work offline?

Assets are cached under `~/.awpy`. Set `AWPY_DATA_DIR` to change this path.
Accessors use cached assets first and download missing assets.
Set `version=` to select a release.
Use `awpy get` or `awpy.data.update()` to check for updates.
See {doc}`visibility`.

## Why do datasets come back instantly the second time?

Dataset properties and individual event DataFrames are cached on the `Demo`.
Use `demo.load(...)` to collect compatible datasets in one pass.
Unrelated datasets are not all prepared on first access.

`player_stats()` caches both values of `include_knife_rounds`.
Its default result is also available as `demo.stats`.
`ticks()` and `snapshots()` run for each call. Keep their results for reuse.

Create a new `Demo` to read the file without the existing caches.

## How can I reduce parse time and memory use?

- Use event frames when you do not need entity state.
- Use `demo.load("kills", "damages", "shots")` for related datasets.
- Select only the properties needed in `ticks(props)`.
- Use `snapshots()` to limit output ticks.
- Reuse cached DataFrames.

Entity decoding can still be required between selected ticks.
A smaller result does not imply an equal reduction in parse time.
See the [benchmark guide](https://github.com/pnxenopoulos/awpy/tree/main/crates/awpy-python/benchmarks).
