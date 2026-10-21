# Awpy

```python
from awpy import Demo

demo = Demo("match.dem")
demo.load("kills", "damages", "shots")
print(demo.header["map_name"])
print(demo.stats.select("name", "kills", "deaths", "assists", "adr", "kast"))
print(demo.snapshots(seconds=1.0))
```

Awpy parses [Counter-Strike 2](https://www.counter-strike.net/cs2) demo files in Rust. Its Python API returns typed [Polars](https://pola.rs) DataFrames.
Use Polars for filters, joins, and Apache Parquet output.
Use matplotlib for radar plots and replay animations.

<a id="why-awpy"></a>

## Use Awpy with Python, Polars, and Rust

- Read match events, rounds, player state, and statistics.
- Select datasets and sample player state at specified ticks.
- Check lines of sight and navigation paths.
- Calculate map control and plot results on radar images.
- Inspect demos and download map assets with the `awpy` command.

<a id="get-started"></a>

## Install Awpy for CS2 replay analysis

Awpy requires Python 3.11 or later and Polars 2.x.

Install with `uv add awpy` or `pip install awpy`. See {doc}`getting-started` and {doc}`examples`. Report problems in [GitHub issues](https://github.com/pnxenopoulos/awpy/issues).



<a id="useful-links"></a>

## Find Awpy and related projects

- [Counter-Strike 2](https://www.counter-strike.net/cs2) — official home page
- [Awpy on GitHub](https://github.com/pnxenopoulos/awpy)
- [LLM documentation index](https://awpy.readthedocs.io/llms.txt)
- [Polars](https://pola.rs) — the DataFrame library Awpy returns data in
- [pbdems2](https://docs.rs/pbdems2/latest/pbdems2/guide/index.html) — the shared Source 2 demo-format core and its format guide
- [Boon](https://github.com/pnxenopoulos/boon) — a Deadlock demo parser
- [deadlock.nyc](https://deadlock.nyc/) — a Deadlock demo viewer for the browser

```{toctree}
:maxdepth: 2
:hidden:
:caption: Start here

getting-started
examples
faq
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Match data

datasets
reference
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Maps & space

visibility
nav
map_control
plot
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Interfaces

api
cli
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: About

other-parsers
changelog
```
