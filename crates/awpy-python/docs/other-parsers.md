# 🧭 Other parsers

Awpy is one of several open-source parsers for Counter-Strike 2 (Source 2)
demos. They differ in language, API style, and focus, and the ecosystem is
better for having more than one — the projects below are worth knowing about,
whether you work in another language or want to cross-check results.

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
event-callback style, one of the parsers above may fit your workflow better.

If you spot another parser that belongs here, please
[open an issue or PR](https://github.com/pnxenopoulos/awpy).
