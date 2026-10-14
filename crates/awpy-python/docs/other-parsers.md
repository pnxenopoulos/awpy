# Other parsers

Use these projects for other games, programming languages, or result comparisons.

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

[**Boon**](https://github.com/pnxenopoulos/boon) parses Deadlock demos.
Like Awpy, it uses pbdems2 with game-specific protobufs, decoders, and datasets.
It provides Rust and Python APIs.

[**deadlock.nyc**](https://deadlock.nyc/) displays Deadlock demos in the browser.

## CS2 demo parsers

- [demoparser2](https://github.com/LaihoE/demoparser): Rust parser with Python and JavaScript bindings.
- [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang): Go parser with event callbacks.
- [clarity](https://github.com/skadistats/clarity): Java parser for Source 2 demos.
- [demofile-net](https://github.com/saul/demofile-net): .NET / C# parser.
