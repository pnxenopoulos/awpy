# ❓ FAQ

## Which games does Awpy support?

Counter-Strike 2 (Source 2) demo files (`.dem`, the
[`PBDEMS2` container](https://docs.rs/pbdems2/latest/pbdems2/guide/file_structure/index.html)).
It does not parse the older CS:GO (Source 1) demo format. For Deadlock (also
Source 2), see the sister project [Boon](https://github.com/pnxenopoulos/boon).

## How do I get Steam ids and names?

The curated datasets already resolve them: `kills` and `damages` carry
`attacker_steamid` / `attacker_name` / `attacker_side` (and the same for the
victim and assister), and `demo.players` is the roster — one row per player
with `steamid`, `name`, and last side.

The exception is **raw event frames** from `demo.events`: keys like `attacker`
there are *user ids* — small, server-assigned slots (e.g. `7`, with `65535`
meaning "none") — because that's what the wire format carries. Prefer the
curated datasets, or join through `demo.players`.

## My demo has no `round_start` / `round_end` events — do rounds still work?

Yes. `rounds` reconstructs rounds from the `CCSGameRules` entity
(`m_totalRoundsPlayed`, `m_bFreezePeriod`, `m_iRoundWinStatus`,
`m_eRoundWinReason`), so it does not depend on those game events. Overtime rounds
are included.

## What are the `winner` numbers?

`2` = terrorist, `3` = counter-terrorist. The `winner_side` column gives the
name. Sides swap at halftime, so a "side" is not a fixed team.

## Why is demo.chat empty?

Server-side (GOTV) recordings — most pro and platform demos — often strip chat
user messages entirely. The schema is still returned, just with zero rows.
Client-recorded demos usually include chat.

## When do map assets download, and can I work offline?

Map assets (radar images, collision meshes, coordinate data) download on first
use and cache under `~/.awpy` (override with `AWPY_DATA_DIR`). Resolution is
**local-first**: once something is cached, no network is involved — analyses
keep working offline and don't shift game versions mid-session. `awpy get` (or
`awpy.data.update()`) is the explicit "check for updates" step, and every
accessor takes `version=` to pin a release. See {doc}`visibility`.

## Why do datasets come back instantly the second time?

Each dataset **property** — `kills`, `damages`, `rounds`, `stats`, and the rest,
plus each event frame from `demo.events` — is computed once and cached on the
`Demo` object, so the first access pays the parse and later accesses hand back
the same DataFrame for free. Touching any one of them warms the others too: the
first access runs a single shared pass that builds most datasets together.

The **methods** are the exception. `ticks()`, `snapshots()`, and `player_stats()`
take arguments, so there's no single result to memoize — they recompute on every
call and cache nothing. Call them once and keep the result. In particular,
`demo.player_stats()` re-runs the whole scoreboard computation each time; use the
cached `demo.stats` property unless you specifically need `include_knife_rounds`.

Open a new `Demo` if you want to drop the caches and re-read the file.

## How fast is it?

The core parser is Rust over a memory-mapped file, and it's **lazy**: constructing
`Demo(path)` only maps the file and checks its magic bytes (microseconds) — no
decoding happens until you touch a dataset. The first heavy access decodes the
demo and builds most of the cached datasets in one parallel pass; everything
after that is free.

What costs what:

- **Event-only frames** (`demo.events[...]`) are cheapest — they read the game
  event stream with no entity pass.
- **Entity-pass datasets** (`kills`, `damages`, `shots`, `stats`) are the costly
  ones: they walk the player entities to resolve positions and state. The shared
  first pass that produces them is roughly **3 seconds on a ~640 MB pro demo**,
  and well under a second on a small (~80 MB) demo.
- **`ticks()` and `snapshots()`** decode in parallel across the demo's keyframes,
  so a full-match `ticks()` is a few seconds while a coarse `snapshots()` stride
  stays cheap no matter how long the demo is (the cost is the decode, not the
  sampled output).
