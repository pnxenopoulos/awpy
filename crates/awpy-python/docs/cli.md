# 💻 Command-line tool

Installing the Python package gives you an `awpy` command (also runnable as
`python -m awpy`) for quick demo inspection and map-data management without
writing any code:

```sh
pip install awpy
awpy --help
```

## Demo inspection

Every command takes a demo path. Row-level commands accept `--limit N`, and
all of them accept `--json` for machine-readable output.

| Command | Description |
| --- | --- |
| `verify` | Check that a file parses as a valid CS2 demo (magic bytes + header). |
| `info` | Print the file header and playback info. |
| `events` | List event names; pass a name to dump that event, `--summary` for counts. |
| `rounds` | Per-round table (start / freeze-end / end / official-end, winner, reason). |
| `kills` | Kills from `player_death`, with players resolved. |
| `damage` | Damage from `player_hurt`, with players + health pre/post. |
| `bomb` | Bomb actions (pickup / drop / plant / defuse) with site. |
| `shots` | Shots from `weapon_fire` with shooter + weapon state. |
| `grenades` / `fires` / `smokes` | Grenade / inferno / smoke summaries. |
| `blinds` | Flash events: who was blinded, by whom, and for how long. |
| `item-events` | Weapon-item transactions: purchases, pickups, and drops. |
| `stats` | Per-player scoreboard (kills, KAST, ADR, openings, trades). |

```sh
awpy info match.dem
awpy rounds match.dem
awpy events match.dem --summary
awpy events match.dem player_ping --json
awpy kills match.dem --limit 20
awpy stats match.dem
```

Tables are rendered by Polars — the same DataFrames the Python API returns —
and `--json` emits the rows as a JSON array:

```text
shape: (24, 9)
┌───────────┬────────────┬─────────────────┬──────────┬───┬───────────────────┬────────────────┐
│ round_num ┆ start_tick ┆ freeze_end_tick ┆ end_tick ┆ … ┆ winner_side       ┆ reason_name    │
╞═══════════╪════════════╪═════════════════╪══════════╪═══╪═══════════════════╪════════════════╡
│ 1         ┆ 1016       ┆ 2712            ┆ 6810     ┆ … ┆ counter-terrorist ┆ bomb_defused   │
│ 2         ┆ 7258       ┆ 11121           ┆ 14649    ┆ … ┆ counter-terrorist ┆ ct_win         │
└───────────┴────────────┴─────────────────┴──────────┴───┴───────────────────┴────────────────┘
```

## Map-data cache

The same command manages the [`awpy-data`](https://github.com/pnxenopoulos/awpy-data)
asset cache under `~/.awpy` (see [Visibility & map data](visibility.md)):

```sh
awpy get             # download the latest release
awpy get 2000873     # ... or a specific one (--force to re-download)
awpy versions        # cached releases, and whether a newer one exists
awpy maps            # maps available in a release
awpy clear 2000873   # delete one cached release (--all for everything)
```

## Parser internals: `awpy-dev`

The Rust workspace additionally ships a developer binary for debugging the
parser itself — the demo message stream, entity snapshots, send-tables, string
tables, and entity classes:

```sh
cargo install --path crates/awpy-dev   # installs `awpy-dev`

awpy-dev messages match.dem --cmd Packet --limit 10
awpy-dev classes match.dem --filter Weapon
awpy-dev send-tables match.dem --filter CCSPlayerPawn
awpy-dev string-tables match.dem --table userinfo
awpy-dev entities match.dem --tick 100000 --class CCSPlayerPawn --fields
```

These surfaces aren't exposed in the Python API; if you're not hacking on the
parser, you won't need them.
