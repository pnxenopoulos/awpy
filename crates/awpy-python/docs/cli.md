# Command-line tool

```sh
pip install awpy
awpy --help
```

Install the package to use `awpy` or `python -m awpy`:



<a id="demo-inspection"></a>

## Inspect CS2 demos with the Awpy CLI

Each inspection command takes a demo path and accepts `--json`.
Dataset commands other than `stats` also accept `--limit N`.

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

Dataset commands print Polars tables. With `--json`, they return row arrays.

<a id="map-data-cache"></a>

## Manage awpy-data with the Awpy CLI

The same command manages the [`awpy-data`](https://github.com/pnxenopoulos/awpy-data)
asset cache under `~/.awpy` (see [Visibility & map data](visibility.md)):

```sh
awpy get             # download the latest release
awpy get 2000873     # ... or a specific one (--force to re-download)
awpy versions        # cached releases, and whether a newer one exists
awpy maps            # maps available in a release
awpy clear 2000873   # delete one cached release (--all for everything)
```

<a id="parser-internals-awpy-dev"></a>

## Inspect Source 2 internals with awpy-dev

Use `awpy-dev` to inspect parser internals:

```sh
cargo install --path crates/awpy-dev   # installs `awpy-dev`

awpy-dev messages match.dem --cmd Packet --limit 10
awpy-dev classes match.dem --filter Weapon
awpy-dev send-tables match.dem --filter CCSPlayerPawn
awpy-dev string-tables match.dem --table userinfo
awpy-dev entities match.dem --tick 100000 --class CCSPlayerPawn --fields
```

These inspection commands are not part of the Python API.
