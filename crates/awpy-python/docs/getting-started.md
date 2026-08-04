# 🚀 Getting started

This is a guided tour of Awpy, start to finish: open a demo, pull structured
datasets, look up players and server settings, reconstruct game state at any
moment, check lines of sight, and draw it all on the map's radar. Every output
below is real — it comes from a professional match played on `de_ancient`.

## Install

Awpy ships as a pre-built wheel with a Rust parser inside — no compiler
required. It supports Python 3.11+.

```sh
uv add awpy          # or: pip install awpy
uv add 'awpy[plot]'  # + matplotlib, for the plotting module
```

## Get a demo

Demos are `.dem` files recorded by the game server. Common sources:

- **Your own matches** — CS2 downloads them under *Watch → Your Matches*, into
  `.../Counter-Strike Global Offensive/game/csgo/replays/`.
- **Pro matches** — HLTV match pages ship GOTV demos for most tier-1 events.
- **Third-party platforms** — FACEIT and other platforms offer demo downloads
  on the match room page.

Awpy parses CS2 (Source 2,
[`PBDEMS2`](https://docs.rs/pbdems2/latest/pbdems2/guide/index.html)) demos. The
older CS:GO format is not supported.

## Open a demo

```python
from awpy import Demo

demo = Demo("match.dem")
```

Construction memory-maps the file and verifies it's a valid CS2 demo — it
raises `FileNotFoundError` or `InvalidDemoError` otherwise, so a `try/except`
around this line is all the validation you need.

The header is a plain dict with the map, server, and playback info:

```python
demo.header["map_name"]        # "de_ancient"
demo.header["playback_time"]   # 2915.94 (seconds)
demo.header["playback_ticks"]  # 186620  -> 64 ticks per second
```

## The datasets

Everything analytical is a property on `Demo` returning a
[Polars](https://pola.rs) DataFrame, parsed on first access and cached:

```python
demo.rounds     # one row per round: ticks, winner, reason
demo.kills      # every player_death, participants fully resolved
demo.damages    # every player_hurt, health/armor before + after
demo.bomb       # plants, defuses, drops, pickups
demo.shots      # every weapon_fire, with shooter/weapon state
demo.grenades   # grenade trajectories, tick by tick
demo.stats      # per-player scoreboard: KAST, ADR, openings, trades
```

Polars makes the follow-up questions one-liners. How did rounds break down by
side?

```python
demo.rounds.group_by("winner_side").len()
# ┌───────────────────┬─────┐
# │ winner_side       ┆ len │
# ╞═══════════════════╪═════╡
# │ counter-terrorist ┆ 21  │
# │ terrorist         ┆ 3   │
# └───────────────────┴─────┘
```

Who led the server, and how clean was their aim?

```python
demo.kills.group_by("attacker_name").len().sort("len", descending=True).head(3)
# ┌───────────────┬─────┐
# │ attacker_name ┆ len │
# ╞═══════════════╪═════╡
# │ blameF        ┆ 23  │
# │ npl           ┆ 21  │
# │ s1zzi         ┆ 20  │
# └───────────────┴─────┘

demo.kills["headshot"].mean()   # 0.446 — 44.6% of kills were headshots
```

The scoreboard is precomputed — including KAST and ADR:

```python
demo.stats.sort("adr", descending=True).select("name", "kills", "deaths", "kast", "adr").head(3)
# ┌────────┬───────┬────────┬───────┬────────┐
# │ name   ┆ kills ┆ deaths ┆ kast  ┆ adr    │
# ╞════════╪═══════╪════════╪═══════╪════════╡
# │ npl    ┆ 19    ┆ 19     ┆ 70.83 ┆ 98.13  │
# │ blameF ┆ 23    ┆ 13     ┆ 87.5  ┆ 97.75  │
# │ JDC    ┆ 19    ┆ 16     ┆ 75.0  ┆ 90.5   │
# └────────┴───────┴────────┴───────┴────────┘
```

Every column of every dataset is documented in {doc}`datasets`.

## Who played, what they said, how the server was set up

```python
demo.players
# ┌───────────────────┬──────────┬───────────┐
# │ steamid           ┆ name     ┆ side      │
# ╞═══════════════════╪══════════╪═══════════╡
# │ 0                 ┆ PWA CSTV ┆ null      │   <- the GOTV bot
# │ 76561198370176682 ┆ gr1ks    ┆ terrorist │
# │ 76561198118196092 ┆ faveN    ┆ terrorist │
# │ ...               ┆ ...      ┆ ...       │
# └───────────────────┴──────────┴───────────┘

demo.chat                       # tick, name, message, channel (may be empty —
                                # server-side recordings often strip chat)

demo.convars["mp_maxrounds"]    # "24"
demo.convars["mp_freezetime"]   # "20"
```

`side` in `players` is the *last* side a player was seen on — sides swap at
halftime, so treat it as "where they finished", not a team identity.

## Any game event

The headline datasets cover the common cases; `demo.events` covers everything
else. It behaves like a read-only mapping from event name to DataFrame:

```python
demo.events.names               # every event in this demo (40 kinds here)
demo.events.counts              # {"player_death": 166, "weapon_fire": 3954, ...}

demo.events.flashbang_detonate  # one event as a DataFrame (133 rows here)
demo.events["player_ping"]      # same thing, by key
```

Event frames are long-form: a `tick` column plus one string column per event
key. Note that raw event keys like `attacker` are *user ids* (server slots),
not Steam ids — use `demo.kills` / `demo.damages` when you want participants
resolved, or join through `demo.players`.

## Game state at any moment

`snapshots` reconstructs every player's state — position, view angles, health,
armor — at a tick, or at every tick in a range:

```python
freeze_end = demo.rounds.row(4, named=True)["freeze_end_tick"]

demo.snapshots(ticks=freeze_end + 640)   # 10 seconds into round 5
# ┌────────┬───────────────────┬────────┬──────────┬─────────┬────────┬─────────┐
# │ name   ┆ side              ┆ health ┆ x        ┆ y       ┆ z      ┆ yaw     │
# ╞════════╪═══════════════════╪════════╪══════════╪═════════╪════════╪═════════╡
# │ JDC    ┆ counter-terrorist ┆ 100    ┆ -967.71  ┆ -147.31 ┆ 92.32  ┆ -36.08  │
# │ faveN  ┆ counter-terrorist ┆ 100    ┆ 1072.47  ┆ 782.02  ┆ 167.17 ┆ -88.98  │
# │ ...    ┆ ...               ┆ ...    ┆ ...      ┆ ...     ┆ ...    ┆ ...     │
# └────────┴───────────────────┴────────┴──────────┴─────────┴────────┴─────────┘

demo.snapshots(start_tick=freeze_end, end_tick=freeze_end + 640)   # every tick of those 10 seconds
```

For arbitrary networked properties beyond what `snapshots` curates, `ticks`
returns one row per player per tick — keyed by `steamid`, natively typed, and
decoded in parallel:

```python
demo.ticks()                              # default: X, Y, Z, health, armor, team_num
demo.ticks(["health", "m_iTeamNum"])
# columns: tick, steamid, health, m_iTeamNum
```

Names accept friendly aliases (`X`/`Y`/`Z` for computed position, `health`,
`armor`, `team_num`, `name`, `money`) or raw CS2 field names.

## Maps: line-of-sight and radar assets

Positions are in world coordinates (Hammer units, Z-up). To reason about them
spatially, Awpy fetches per-map assets — collision meshes, radar images, and
coordinate transforms — from [awpy-data](https://github.com/pnxenopoulos/awpy-data),
downloading on first use and caching under `~/.awpy`:

```python
from awpy import VisibilityChecker

vc = VisibilityChecker(demo.header["map_name"])   # downloads the mesh if needed

kill = demo.kills.row(0, named=True)
vc.is_visible(
    (kill["attacker_x"], kill["attacker_y"], kill["attacker_z"]),
    (kill["victim_x"], kill["victim_y"], kill["victim_z"]),
)  # True — a clean line of sight (this one was an AWP pick)
```

Pin a game version with `version=` (an integer ClientVersion like `2000873`),
or manage the cache from the shell: `awpy get`, `awpy versions`, `awpy clear`.
See {doc}`visibility`.

## Draw it

With the `awpy[plot]` extra, `awpy.plot` renders game states and heatmaps on
the map's radar image. Death locations for the whole match:

```python
from awpy import plot

deaths = demo.kills.select(["victim_x", "victim_y", "victim_z"]).rows()
fig, ax = plot.heatmap(demo.header["map_name"], deaths, method="kde")
fig.savefig("deaths.png")
```

And because `snapshots` rows carry exactly what a marker needs, any moment of
the match is a frame:

```python
snap = demo.snapshots(ticks=freeze_end + 640)
players = [
    plot.Player(x=r["x"], y=r["y"], z=r["z"], yaw=r["yaw"], hp=r["health"],
                armor=r["armor"], side=r["side"], label=r["name"])
    for r in snap.iter_rows(named=True)
]
fig, ax = plot.frame(demo.header["map_name"], players)
fig.savefig("round5.png")
```

Multi-level maps, animated GIFs, and layered plots are covered in {doc}`plot`.

## The command line

Everything above has a no-code counterpart — installing the package installs
the `awpy` command:

```sh
awpy info match.dem              # header + playback info
awpy stats match.dem             # the scoreboard
awpy kills match.dem --limit 10  # first ten kills
awpy events match.dem --summary  # event counts
awpy rounds match.dem --json     # any table as JSON
awpy get                         # prefetch the latest map assets
```

See {doc}`cli` for the full command list.

## Where next

- {doc}`examples` — complete, runnable scripts: scoreboards, trade graphs, buy-type
  win rates, clutch GIFs, and batch parsing to Parquet.
- {doc}`datasets` — every dataset, every column.
- {doc}`plot` — frames, heatmaps, multi-level maps, GIFs.
- {doc}`visibility` — line-of-sight, map data, and the asset cache.
- {doc}`api` — the full API reference.
- {doc}`faq` — common questions and sharp edges.
