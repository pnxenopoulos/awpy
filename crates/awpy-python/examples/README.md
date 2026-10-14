# Awpy examples

Each script takes a demo path. CI tests these scripts with a demo.

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

## Sample size

Do not draw conclusions from one match.
Use `batch_parse.py` to prepare multiple demos for analysis.
