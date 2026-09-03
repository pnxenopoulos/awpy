# awpy

Core library for parsing **Counter-Strike 2** demo (`.dem`) files.

```rust
use std::path::Path;
use awpy::Parser;

let parser = Parser::from_file(Path::new("match.dem"))?;
let header = parser.file_header()?;
println!("map: {:?}", header.map_name);
# Ok::<(), awpy::Error>(())
```

## What it does

- Reads the Source 2 `PBDEMS2` container: command stream, Snappy decompression,
  string tables, flattened serializers, class info.
- Decodes game events (`player_death`, `round_end`, `weapon_fire`, …) with their
  key/value payloads.
- Decodes the entity system tick by tick (`run_to_end`), including CS2-specific
  field encodings (clip ammo, polymorphic game-mode rules, binary blocks,
  `CTransform`/`Quaternion` vectors).
- Provides name lookups: [`team_name`], [`hitgroup_name`],
  [`round_end_reason_name`], [`game_phase_name`], and world-position helpers.

## Entry points

- [`Parser::file_header`] / [`Parser::file_info`] — metadata.
- [`Parser::messages`] — enumerate the command stream.
- [`Parser::events`] — collect game events.
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

Part of the [Awpy](https://github.com/pnxenopoulos/awpy) workspace.

## License

MIT
