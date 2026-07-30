# 🧪 Examples

Complete, runnable scripts live in
[`crates/awpy-python/examples/`](https://github.com/pnxenopoulos/awpy/tree/main/crates/awpy-python/examples)
in the repository. Each one takes a demo path on the command line and is
smoke-tested against a real demo in CI, so they stay in step with the API.

```sh
python scoreboard.py match.dem
```

## `scoreboard.py` — start here

Round-by-round results plus an end-of-match scoreboard, both teams in one table.
Knife rounds are excluded throughout. Touches {doc}`rounds, stats, and players
<datasets>` and uses `demo.tick_rate` to report round lengths in seconds.

## `trades.py` — who refrags for whom

`demo.kills` flags both halves of a trade: `is_trade` on the avenging kill, and
`victim_traded` on the death it avenged. Pairing them turns a flat kill list into a
directed graph — who reliably picks up refrags, and whose deaths go unanswered.
That pairing is not something a single column gives you.

## `economy.py` — does forcing work?

Joins `demo.round_economy` to `demo.rounds` for win rate by buy type, overall and
per side. One match is far too small a sample to conclude anything from; the join
is the reusable part.

## `clutch_reel.py` — from stats to video

Locates every 1-vs-many situation by replaying each round's kills, then renders
each as an animated radar GIF. Chains three subsystems: `rounds` + `kills` to find
the moment, `snapshots` to reconstruct positions, and {func}`awpy.plot.gif` to
draw it. Needs the plot extra (`pip install 'awpy[plot]'`).

## `batch_parse.py` — a folder of demos to Parquet

Turns a directory of `.dem` files into columnar tables, one Parquet file per
dataset, each row tagged with its source demo. Writes incrementally, so an
interrupted run keeps the demos already finished. This is the practical starting
point for any analysis spanning more than one match — parse once, then query with
`pl.scan_parquet` without touching a demo again.

## Shorter snippets

For inline examples of individual datasets and columns, see {doc}`datasets`; for
plotting recipes specifically, see {doc}`plot`.
