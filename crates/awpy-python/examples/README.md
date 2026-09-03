# Awpy examples

Runnable scripts, each self-contained and each taking a demo path on the command
line. They are smoke-tested against a real demo in CI (see
`tests/test_examples.py`), so they cannot silently rot as the API changes.

```sh
pip install awpy          # or: pip install 'awpy[plot]' for clutch_reel.py
python scoreboard.py match.dem
```

| Script | What it shows |
| --- | --- |
| [`scoreboard.py`](scoreboard.py) | Start here. Round-by-round results and an end-of-match scoreboard, both teams in one table. Touches `rounds`, `stats`, `players`, `tick_rate`. |
| [`trades.py`](trades.py) | Pairs each trade kill with the death it avenged, turning `kills` into a "who refrags for whom" graph. Uses the `is_trade` / `victim_traded` flags. |
| [`economy.py`](economy.py) | Win rate by buy type, joining `round_economy` to `rounds`. |
| [`clutch_reel.py`](clutch_reel.py) | Locates every 1-vs-many situation, then renders each as a radar GIF. Chains `rounds` + `kills` → `snapshots` → `awpy.plot.gif`. Needs `awpy[plot]`. |
| [`batch_parse.py`](batch_parse.py) | A folder of demos → Parquet, one file per table, so later analysis never re-parses. |

## Getting a demo

- **Your own matches** — CS2 writes them under *Watch → Your Matches*, into
  `.../Counter-Strike Global Offensive/game/csgo/replays/`.
- **Pro matches** — HLTV match pages carry GOTV demos for most tier-1 events.
- **Third-party platforms** — FACEIT and similar offer downloads on the match page.

Awpy reads CS2 (Source 2, `PBDEMS2`) demos; the older CS:GO format is not
supported.

## A note on sample size

`economy.py` and `trades.py` compute rates from a single match, which is far too
small a sample to draw conclusions from. The reusable part is the join, not the
number — run them across many demos (start from `batch_parse.py`) before believing
anything.
