# Examples

These scripts take a demo path. CI tests them with a demo.
Source files are in [examples](https://github.com/pnxenopoulos/awpy/tree/main/crates/awpy-python/examples).

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

Pair `is_trade` and `victim_traded` kills to count which players avenge each other.

```{literalinclude} ../examples/trades.py
:language: python
:caption: examples/trades.py
```

The trade flags identify same-team pairs:

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
per side. Use multiple matches before drawing conclusions.

```{literalinclude} ../examples/economy.py
:language: python
:caption: examples/economy.py
```

## clutch_reel.py — from stats to video

Find clutches from round kills, sample player positions, and render GIFs.
Requires `pip install 'awpy[plot]'`.

```{literalinclude} ../examples/clutch_reel.py
:language: python
:caption: examples/clutch_reel.py
```

## batch_parse.py — a folder of demos to Parquet

Write one Parquet file per dataset and include the source demo in each row.
Completed demos remain available if the run stops.
Use `pl.scan_parquet` to query results without parsing again.

```{literalinclude} ../examples/batch_parse.py
:language: python
:caption: examples/batch_parse.py
```
