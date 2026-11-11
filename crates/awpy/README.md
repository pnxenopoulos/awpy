# awpy

```rust
use std::path::Path;
use awpy::Parser;

fn main() -> awpy::Result<()> {
    let parser = Parser::from_file(Path::new("match.dem"))?;
    let header = parser.file_header()?;
    println!("map: {:?}", header.map_name);
    Ok(())
}
```

Core library for parsing **Counter-Strike 2** demo (`.dem`) files.



<a id="what-it-does"></a>

## Read CS2 data with the Awpy Rust crate

- Uses [pbdems2](https://docs.rs/pbdems2/latest/pbdems2/) for shared Source 2 decoding.
- Adds CS2 field decoders, datasets, and name tables.
- Returns game events and per-tick entity state.

<a id="entry-points"></a>

## Select Awpy Rust parser methods

- [`Parser::file_header`] / [`Parser::file_info`] — metadata.
- [`Parser::messages`] — enumerate the command stream.
- [`Parser::events`] — collect game events.
- `Parser::events_with_players` — read legacy events with player data.
- [`Parser::parse_init`] — serializers, classes, string tables.
- [`Parser::parse_to_tick`] — game state snapshot at a tick.
- [`Parser::run_to_end`] — a callback per tick with the live entity set.
- Structured datasets: [`Parser::rounds`], [`Parser::kills`],
  [`Parser::damages`], [`Parser::bomb`], [`Parser::blinds`], [`Parser::shots`],
  [`Parser::grenades`], [`Parser::fires`], [`Parser::smokes`],
  [`Parser::item_events`], [`Parser::players`], [`Parser::chat`],
  [`Parser::player_stats`].
- Per-player state: [`Parser::snapshots`] (a tick range) and
  [`Parser::snapshots_sampled`] (a stride / event ticks), decoded in parallel
  across keyframe segments.

## Read legacy CS2 events with Awpy player data

```rust
use std::collections::HashSet;
use std::path::Path;

use awpy::Parser;

fn main() -> awpy::Result<()> {
    let parser = Parser::from_file(Path::new("match.dem"))?;
    let names = HashSet::from(["player_death", "bomb_pickup"]);
    let events = parser.events_with_players(&names)?;
    println!("Read {} events", events.len());
    Ok(())
}
```

Awpy resolves participants from entity and `userinfo` data at the end of the
event tick. It uses the event's pawn handle when available. The slot fallback
requires a full user ID match and checks the Steam ID when recorded. If Awpy
cannot identify a participant, its player fields can be `None`.

Part of the [Awpy](https://github.com/pnxenopoulos/awpy) workspace.

## License

MIT
