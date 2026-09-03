# 🧪 Examples

Five complete scripts, each taking a demo path on the command line. The source
below is included straight from
[`crates/awpy-python/examples/`](https://github.com/pnxenopoulos/awpy/tree/main/crates/awpy-python/examples),
and every one is smoke-tested against a real demo in CI — so what you read here
is code that runs.

```sh
python scoreboard.py match.dem
```

For inline snippets of individual datasets and columns, see {doc}`datasets`; for
plotting recipes, see {doc}`plot`.

## scoreboard.py — start here

Round-by-round results plus an end-of-match scoreboard, both teams in one table.
Touches `rounds`, `stats`, and `players`, and uses `demo.tick_rate` to report
round lengths in seconds.

```{literalinclude} ../examples/scoreboard.py
:language: python
:caption: examples/scoreboard.py
```

Output on a professional match:

```text
de_inferno  (64 tick)

Rounds (17)
----------------------------------------------------------
  #  winner             reason                     time
  1  terrorist          terrorists_win              72s
  2  terrorist          terrorists_win             129s
  3  terrorist          target_bombed              122s
...

Scoreboard (17 rounds)
------------------------------------------------------------------------
player          team           K     D     A    HS    FA    TR    CL   ADR  KAST
buda            BESTIA        16    13     1    12     0     4     0  88.6  76.5
decenty         Imperial      16     7     2    11     0     1     2  92.9  70.6
vini            Imperial      14    10     6     7     2     3     1  76.8  76.5
chelo           Imperial      12    12     4     6     0     4     0  90.4  70.6
saadzin         Imperial      12    11     3     5     2     3     0  71.4  70.6
```

## trades.py — who refrags for whom

`demo.kills` flags both halves of a trade: `is_trade` on the avenging kill,
`victim_traded` on the death it avenged. Pairing them turns a flat kill list into
a directed graph — who reliably picks up refrags, and whose deaths go unanswered.
That pairing is not something a single column gives you.

```{literalinclude} ../examples/trades.py
:language: python
:caption: examples/trades.py
```

Note that the reconstruction is never told which players are teammates; it
recovers that from the flags alone, so every pair it produces is same-team:

```text
Trade pairs (20 reconstructed)
------------------------------------------------
decenty          -> saadzin             2
noway            -> chelo               2
vini             -> chelo               2
tomaszin         -> buda                2
```

## economy.py — does forcing work?

Joins `demo.round_economy` to `demo.rounds` for win rate by buy type, overall and
per side. One match is far too small a sample to conclude anything from — the join
is the reusable part.

```{literalinclude} ../examples/economy.py
:language: python
:caption: examples/economy.py
```

## clutch_reel.py — from stats to video

Locates every 1-vs-many situation by replaying each round's kills, then renders
each as an animated radar GIF. Chains three subsystems: `rounds` + `kills` to find
the moment, `snapshots` to reconstruct positions, and {func}`awpy.plot.gif` to draw
it. Needs the plot extra (`pip install 'awpy[plot]'`).

```{literalinclude} ../examples/clutch_reel.py
:language: python
:caption: examples/clutch_reel.py
```

## batch_parse.py — a folder of demos to Parquet

Turns a directory of `.dem` files into columnar tables, one Parquet file per
dataset, each row tagged with its source demo. Writes incrementally, so an
interrupted run keeps the demos already finished. This is the practical starting
point for any analysis spanning more than one match — parse once, then query with
`pl.scan_parquet` without touching a demo again.

```{literalinclude} ../examples/batch_parse.py
:language: python
:caption: examples/batch_parse.py
```
