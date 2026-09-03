# 🧭 Other parsers

Awpy is one of several open-source parsers for Counter-Strike 2 (Source 2)
demos. They differ in language, API style, and focus, and the ecosystem is
better for having more than one — the projects below are worth knowing about,
whether you work in another language or want to cross-check results.

## Shared Source 2 core: pbdems2

[**pbdems2**](https://github.com/pnxenopoulos/pbdems2) is the game-neutral Rust
crate beneath Awpy and Boon. It handles the `PBDEMS2` container, command and
packet framing, flattened serializers and field paths, string tables, entity
state, and playback and seeking. The game adapters supply their own protobufs,
field decoders, name tables, and higher-level datasets.

Its [PBDEMS2 format guide](https://docs.rs/pbdems2/latest/pbdems2/guide/index.html)
is the canonical reference for these shared internals. It includes focused
chapters on [file structure](https://docs.rs/pbdems2/latest/pbdems2/guide/file_structure/index.html),
[packet messages](https://docs.rs/pbdems2/latest/pbdems2/guide/packet_messages/index.html),
[flattened serializers](https://docs.rs/pbdems2/latest/pbdems2/guide/serializers/index.html),
[string tables](https://docs.rs/pbdems2/latest/pbdems2/guide/string_tables/index.html),
[entities](https://docs.rs/pbdems2/latest/pbdems2/guide/entities/index.html), and
[playback and seeking](https://docs.rs/pbdems2/latest/pbdems2/guide/playback/index.html).

## Sister project: Boon

[**Boon**](https://github.com/pnxenopoulos/boon) is Awpy's sister project — a
demo parser for [Deadlock](https://store.steampowered.com/app/1422450/Deadlock/),
built by the same author with the same design: a Rust core, native Python
bindings, and [Polars](https://pola.rs) DataFrames out.

Deadlock and Counter-Strike 2 both run on **Source 2**, so both projects build on
pbdems2. What differs is the game-specific layer, and that's what each supplies:
its own protobuf definitions, a handful of game-specific field decoders, name
tables, and higher-level datasets. If you've used one, the other will feel
immediately familiar.

There's also [**deadlock.nyc**](https://deadlock.nyc/), a fully client-side
Deadlock demo viewer that runs in the browser.

## CS2 demo parsers

- **[demoparser2](https://github.com/LaihoE/demoparser)** — a fast Rust parser
  with first-class **Python** and **JavaScript** bindings that also returns
  tabular data (Polars / pandas). The closest in spirit to Awpy, and a great
  reference point.
- **[demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang)** — the
  established **Go** parser, built around an event-driven callback API. Mature,
  widely used in production, and thoroughly documented.
- **[clarity](https://github.com/skadistats/clarity)** — a high-performance
  **Java** parser for Source 2 demos (CS2 and Dota 2), long a cornerstone of the
  Dota 2 parsing community.
- **[demofile-net](https://github.com/saul/demofile-net)** — a **.NET / C#**
  parser with a clean, strongly-typed API over the entity and game-event
  streams.

## How Awpy fits

Awpy pairs a Rust core with Python bindings and returns
[Polars](https://pola.rs) DataFrames, aiming to get you from a `.dem` file to
analysis-ready tables (`kills`, `damages`, `rounds`, `blinds`, `snapshots`, …) in
as few lines as possible. If you need a different language or a lower-level,
event-callback style, one of the CS2 parsers above may fit your workflow better —
and if you're working with Deadlock rather than CS2, reach for Boon.

If you spot another parser that belongs here, please
[open an issue or PR](https://github.com/pnxenopoulos/awpy).
