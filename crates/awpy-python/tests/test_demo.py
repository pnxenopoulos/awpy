"""Tests for the awpy Python bindings.

The fixture-backed tests are skipped when no demo is present (see conftest).
The error-handling tests always run.
"""

from pathlib import Path

import polars as pl
import pytest
from awpy import Demo, InvalidDemoError


def test_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        Demo("does-not-exist.dem")


def test_invalid_file_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.dem"
    bogus.write_bytes(b"not a demo file at all")
    with pytest.raises(InvalidDemoError):
        Demo(bogus)


def test_header(demo_path: Path) -> None:
    demo = Demo(demo_path)
    header = demo.header
    assert isinstance(header, dict)
    assert "map_name" in header
    assert header["map_name"].startswith("de_")


def test_events_listing(demo_path: Path) -> None:
    events = Demo(demo_path).events
    assert "player_death" in events
    assert "player_death" in events.names
    assert list(events) == events.names == sorted(events.names)
    assert len(events) == len(events.names)
    assert events.counts["player_death"] > 0
    assert "player_death" in repr(events)


def test_events_access_and_caching(demo_path: Path) -> None:
    demo = Demo(demo_path)
    deaths = demo.events.player_death
    assert isinstance(deaths, pl.DataFrame)
    assert "tick" in deaths.columns
    assert "attacker" in deaths.columns
    assert deaths.height > 0
    # Item access hits the same cached frame; the accessor itself is cached too.
    assert demo.events["player_death"] is deaths
    assert demo.events is demo.events


def test_events_unknown_name_raises(demo_path: Path) -> None:
    events = Demo(demo_path).events
    with pytest.raises(KeyError, match="no_such_event"):
        events["no_such_event"]
    with pytest.raises(AttributeError, match="no_such_event"):
        _ = events.no_such_event


def test_parse_ticks(demo_path: Path) -> None:
    demo = Demo(demo_path)
    # Default props: one row per player per tick, keyed by steamid, with computed
    # world position and core state.
    ticks = demo.ticks()
    assert isinstance(ticks, pl.DataFrame)
    assert {"tick", "steamid", "X", "Y", "Z", "health", "armor", "team_num"} <= set(ticks.columns)
    assert ticks.height > 0
    # Identity is complete (filled from the global slot map) and unique per tick:
    # no pawn/controller double-emission.
    assert ticks["steamid"].is_null().sum() == 0
    assert ticks.select(["tick", "steamid"]).n_unique() == ticks.height
    # A standard match has 10 humans; each tick should have ~10 player rows.
    per_tick = ticks.group_by("tick").len()["len"]
    assert per_tick.max() <= 12  # 10 players (+ occasional connecting/GOTV)
    assert per_tick.median() >= 8
    # X/Y/Z are world coordinates (computed from cell + offset), not raw offsets.
    assert ticks["X"].abs().max() > 100.0
    # Health is a sane 0..100.
    assert 0 <= ticks["health"].min() and ticks["health"].max() <= 100

    # Friendly aliases and raw names both work; a pawn field (team) and a
    # controller field (name) resolve in one call.
    named = demo.ticks(["m_iTeamNum", "name", "velocity_x", "velocity"])
    assert {
        "tick",
        "steamid",
        "m_iTeamNum",
        "name",
        "velocity_x",
        "velocity",
    } <= set(named.columns)
    assert named["m_iTeamNum"].is_not_null().any()
    assert named["name"].is_not_null().any()
    assert named["velocity_x"].is_not_null().any()
    assert named["velocity"].max() > 0

    # players_only=False still dumps every entity separately.
    raw = demo.ticks(["m_iTeamNum"], players_only=False)
    assert {
        "tick",
        "entity_id",
        "entity_serial",
        "class_name",
        "m_iTeamNum",
    } <= set(raw.columns)
    assert raw.height > ticks.height


def test_snapshots_parallel_matches_serial(
    demo_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Snapshots decode in parallel across keyframe segments (including the loadout,
    # which follows weapon-entity handles); the result must be bit-identical to a
    # single serial pass.
    keys = ["tick", "steamid"]
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "1")
    serial = Demo(demo_path).snapshots(every=64)
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "8")
    parallel = Demo(demo_path).snapshots(every=64)
    assert parallel.height == serial.height
    assert serial.sort(keys).equals(parallel.sort(keys))


def test_ticks_parallel_matches_serial(demo_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ticks() decodes the demo in parallel across keyframe segments; the result
    # must be bit-identical to a single serial pass (AWPY_TICK_SEGMENTS forces the
    # segment count).
    keys = ["tick", "steamid"]
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "1")
    serial = Demo(demo_path).ticks()
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "8")
    parallel = Demo(demo_path).ticks()
    assert parallel.height == serial.height
    assert serial.sort(keys).equals(parallel.sort(keys))


def test_players(demo_path: Path) -> None:
    players = Demo(demo_path).players
    assert isinstance(players, pl.DataFrame)
    assert {"steamid", "name", "side", "team_clan_name"} <= set(players.columns)
    humans = players.filter(pl.col("steamid") > 0)
    assert humans.height == 10
    assert humans["steamid"].n_unique() == 10
    assert set(humans["side"].unique()) <= {"terrorist", "counter-terrorist"}


def test_players_team_clan_names(demo_path: Path) -> None:
    players = Demo(demo_path).players
    playing = players.filter(pl.col("side").is_in(["terrorist", "counter-terrorist"]))
    named = playing.drop_nulls("team_clan_name")
    if named.is_empty():
        pytest.skip("demo has no team clan names (casual matchmaking)")

    # A clan belongs to one side at a time, so a named match has at most two.
    assert named["team_clan_name"].n_unique() <= 2
    assert all(clan.strip() for clan in named["team_clan_name"])
    # Everyone sharing a side shares a clan: the name is read alongside the side,
    # so the two can never describe different moments.
    per_side = named.group_by("side").agg(pl.col("team_clan_name").n_unique().alias("clans"))
    assert (per_side["clans"] == 1).all()
    # Spectators and unassigned players are on no team, so they carry no clan.
    bench = players.filter(~pl.col("side").is_in(["terrorist", "counter-terrorist"]))
    assert bench["team_clan_name"].null_count() == bench.height


def test_tick_rate(demo_path: Path) -> None:
    demo = Demo(demo_path)
    assert isinstance(demo.tick_rate, float)
    # Every competitive demo is 64 or 128 tick; the fallback is 64.
    assert demo.tick_rate in (64.0, 128.0)
    # Consistent with the header's own playback timing, when it reports it.
    header = demo.header
    ticks, seconds = header.get("playback_ticks"), header.get("playback_time")
    if ticks and seconds:
        assert demo.tick_rate == pytest.approx(ticks / seconds, rel=1e-3)


def test_snapshot_single_tick(demo_path: Path) -> None:
    demo = Demo(demo_path)
    tick = demo.rounds.row(0, named=True)["freeze_end_tick"]
    snap = demo.snapshots(ticks=tick)
    assert {
        "tick",
        "steamid",
        "name",
        "side",
        "health",
        "armor",
        "x",
        "y",
        "z",
        "velocity_x",
        "velocity_y",
        "velocity_z",
        "velocity",
        "pitch",
        "yaw",
    } <= set(snap.columns)
    assert snap.height == 10  # every player, alive at freeze end
    assert snap["tick"].unique().to_list() == [tick]
    assert snap["health"].min() == 100
    assert snap["x"].null_count() == 0
    assert snap["velocity_x"].null_count() == 0
    assert snap["velocity"].min() >= 0
    # Snapshots must work anywhere in the demo, not just near full packets.
    for probe in (2000, 29000, 60000, 150000):
        assert demo.snapshots(ticks=probe).height == 10, f"empty snapshot at tick {probe}"


def test_snapshot_tick_range(demo_path: Path) -> None:
    demo = Demo(demo_path)
    start = demo.rounds.row(0, named=True)["freeze_end_tick"]
    span = demo.snapshots(start_tick=start, end_tick=start + 128)
    ticks = span["tick"]
    assert ticks.min() >= start and ticks.max() <= start + 128
    assert ticks.n_unique() > 1
    assert span.height == ticks.n_unique() * 10


def test_snapshots_sampled(demo_path: Path) -> None:
    demo = Demo(demo_path)

    # `every=N`: evenly spaced ticks, same schema as a single snapshot, 10 players each.
    every = demo.snapshots(every=256)
    one = demo.snapshots(ticks=demo.rounds["freeze_end_tick"][0])
    assert set(every.columns) == set(one.columns)
    gaps = every["tick"].unique().sort().diff().drop_nulls()
    assert gaps.min() >= 256 and gaps.max() == 256  # gap-robust stride hits exactly N
    assert every.height == every["tick"].n_unique() * 10
    # Weapons must resolve in the sampled pass, not just single snapshot() — the
    # filtered decode has to keep weapon entities, else the loadout is all null.
    assert every["primary_weapon"].drop_nulls().len() > 0
    assert every.filter(pl.col("inventory") != "").height > 0

    # `seconds=S` converts via the tick rate (64-tick demo -> 256-tick stride).
    per_sec = demo.snapshots(seconds=4.0)
    assert per_sec["tick"].unique().sort().diff().drop_nulls().max() == 256

    # `events=` samples exactly the ticks those events fired on (they are real
    # frame ticks, so every kill tick is present).
    kill_ticks = set(demo.kills["tick"].to_list())
    on_kills = demo.snapshots(events="player_death")
    assert set(on_kills["tick"].to_list()) == kill_ticks

    # Explicit ticks (drawn from real frames), and the stride ∪ events union.
    some_ticks = every["tick"].unique().to_list()[:3]
    picked = demo.snapshots(ticks=some_ticks)
    assert set(picked["tick"].to_list()) == set(some_ticks)
    union = demo.snapshots(every=256, events="player_death")
    assert kill_ticks <= set(union["tick"].to_list())
    assert set(every["tick"].to_list()) <= set(union["tick"].to_list())

    # Selectors are required, and every/seconds are mutually exclusive.
    with pytest.raises(ValueError):
        demo.snapshots()
    with pytest.raises(ValueError):
        demo.snapshots(every=64, seconds=1.0)


def test_snapshot_economy(demo_path: Path) -> None:
    demo = Demo(demo_path)
    # Freeze end of the first (pistol) round: all 10 players alive and armed.
    tick = demo.rounds.row(0, named=True)["freeze_end_tick"]
    snap = demo.snapshots(ticks=tick)
    econ = {
        "health",
        "armor",
        "has_helmet",
        "has_defuser",
        "has_bomb",
        "active_weapon",
        "primary_weapon",
        "secondary_weapon",
        "fire_grenades",
        "smoke_grenades",
        "he_grenades",
        "flashbangs",
        "decoy_grenades",
        "equipment_value",
        "equipment_value_round_start",
        "money",
        "is_crouched",
        "is_walking",
        "is_jumping",
        "is_in_bomb_zone",
        "is_scoped",
        "is_defusing",
        "flash_duration",
        "inventory",
    }
    assert econ <= set(snap.columns)
    assert snap.height == 10
    assert snap["equipment_value"].dtype == pl.Int32
    # Every alive player bought something and carries a knife.
    assert (snap["equipment_value"] > 0).all()
    assert snap["inventory"].str.contains("knife").all()
    # Pistol round: everyone has a pistol, nobody has a rifle.
    assert snap["secondary_weapon"].null_count() == 0
    assert snap["primary_weapon"].null_count() == 10
    # Exactly one player carries the bomb.
    assert snap["has_bomb"].sum() == 1
    # Money is a sane amount and typed; the active weapon resolves for everyone.
    assert snap["money"].min() >= 0
    assert snap["active_weapon"].null_count() == 0
    # Grenade counts are non-negative; the loadout never lists two bombs (the
    # over-scan bug that a stale inventory slot would cause).
    for col in ("he_grenades", "flashbangs", "smoke_grenades", "fire_grenades", "decoy_grenades"):
        assert snap[col].min() >= 0
    assert (snap["inventory"].str.count_matches("c4") <= 1).all()
    # The primary/secondary names, when present, appear in the inventory string.
    for row in snap.iter_rows(named=True):
        if row["secondary_weapon"]:
            assert row["secondary_weapon"] in row["inventory"]


def test_blinds(demo_path: Path) -> None:
    blinds = Demo(demo_path).blinds
    assert isinstance(blinds, pl.DataFrame)
    expected = {
        "tick",
        "attacker_steamid",
        "attacker_name",
        "attacker_side",
        "victim_steamid",
        "victim_name",
        "victim_side",
        "victim_x",
        "victim_y",
        "victim_z",
        "duration",
    }
    assert expected <= set(blinds.columns)
    assert blinds["duration"].dtype == pl.Float32
    # Demos without flashbang_detonate (rare) yield an empty frame; the fixture
    # is a real match, so it has flashes.
    if blinds.height:
        assert (blinds["duration"] > 0).all()
        assert blinds["duration"].max() <= 6.0  # engine flash cap is ~5 s
        # Every blinded victim is resolved to a side and a position.
        assert blinds["victim_side"].null_count() == 0
        assert set(blinds["victim_side"].unique()) <= {"terrorist", "counter-terrorist"}
        assert blinds["victim_x"].null_count() == 0
        # Rows are in tick order.
        assert blinds["tick"].to_list() == sorted(blinds["tick"].to_list())


def test_item_events(demo_path: Path) -> None:
    items = Demo(demo_path).item_events
    assert isinstance(items, pl.DataFrame)
    expected = {
        "tick",
        "action",
        "steamid",
        "name",
        "side",
        "item",
        "x",
        "y",
        "z",
        "original_owner_steamid",
        "cost",
        "near_buy_zone",
    }
    assert expected <= set(items.columns)
    assert items.height > 0
    assert set(items["action"].unique()) <= {"purchase", "pickup", "drop"}
    # The knife is excluded (default loadout, never bought/dropped meaningfully).
    assert "knife" not in set(items["item"].unique())
    # Rows are in tick order.
    assert items["tick"].to_list() == sorted(items["tick"].to_list())

    purchases = items.filter(pl.col("action") == "purchase")
    assert purchases.height > 0
    # A purchase is the buyer's own weapon, at a plausible cost (never a money
    # reset, which would show as a huge "cost").
    assert (purchases["original_owner_steamid"] == purchases["steamid"]).all()
    assert purchases["cost"].min() > 0
    assert purchases["cost"].max() <= 6500
    # Pickups and drops carry no cost.
    non_purchase = items.filter(pl.col("action") != "purchase")
    assert non_purchase["cost"].null_count() == non_purchase.height
    # Drops record whether they happened near a buy zone.
    drops = items.filter(pl.col("action") == "drop")
    if drops.height:
        assert drops["near_buy_zone"].null_count() == 0


def test_chat(demo_path: Path) -> None:
    demo = Demo(demo_path)
    chat = demo.chat
    assert isinstance(chat, pl.DataFrame)
    # Server-side demos may strip chat entirely; the schema must hold anyway.
    assert {"tick", "entity_index", "name", "message", "channel"} <= set(chat.columns)
    say_text_count = sum(
        count for name, count in demo.events.counts.items() if "saytext" in name.lower()
    )
    assert chat.height == say_text_count
    if chat.height:
        assert chat["message"].null_count() == 0
    else:
        assert say_text_count == 0


def test_convars(demo_path: Path) -> None:
    convars = Demo(demo_path).convars
    assert isinstance(convars, dict)
    assert convars  # every demo carries at least the signon convars
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in convars.items())
    assert any(key.startswith("mp_") for key in convars)


def test_rounds(demo_path: Path) -> None:
    demo = Demo(demo_path)
    rounds = demo.rounds
    assert isinstance(rounds, pl.DataFrame)
    assert {
        "round_num",
        "start_tick",
        "freeze_end_tick",
        "end_tick",
        "winner",
        "winner_side",
        "reason_name",
    } <= set(rounds.columns)
    assert rounds.height > 0
    # Winners are terrorist / counter-terrorist.
    assert set(rounds["winner_side"].unique()) <= {"terrorist", "counter-terrorist"}
    # End ticks are strictly increasing across rounds.
    end = rounds["end_tick"].to_list()
    assert end == sorted(end)


def test_kills(demo_path: Path) -> None:
    demo = Demo(demo_path)
    kills = demo.kills
    assert isinstance(kills, pl.DataFrame)
    expected = {
        "attacker_steamid",
        "attacker_name",
        "attacker_side",
        "attacker_x",
        "attacker_y",
        "attacker_z",
        "victim_steamid",
        "victim_name",
        "victim_side",
        "victim_x",
        "victim_y",
        "victim_z",
        "assister_steamid",
        "assister_name",
        "assister_side",
        "weapon",
        "headshot",
        "hitgroup_name",
        "tick",
    }
    assert expected <= set(kills.columns)
    assert kills.height > 0
    assert kills["headshot"].dtype == pl.Boolean
    assert kills["attacker_x"].dtype == pl.Float32
    assert kills["attacker_steamid"].dtype == pl.UInt64
    # Sides are terrorist / counter-terrorist (or null for world kills).
    sides = set(kills["attacker_side"].drop_nulls().unique())
    assert sides <= {"terrorist", "counter-terrorist"}


def test_damages(demo_path: Path) -> None:
    demo = Demo(demo_path)
    damages = demo.damages
    assert isinstance(damages, pl.DataFrame)
    assert {
        "attacker_name",
        "victim_name",
        "weapon",
        "dmg_health",
        "hitgroup_name",
        "health_pre",
        "health_post",
        "armor_pre",
        "armor_post",
        "tick",
    } <= set(damages.columns)
    assert damages.height > 0
    # Pre-health is health_post + dmg_health, clamped to the 100 HP maximum
    # (raw damage can exceed remaining health on a lethal hit).
    bad = damages.filter(
        pl.col("health_pre")
        != pl.min_horizontal(pl.col("health_post") + pl.col("dmg_health"), pl.lit(100))
    )
    assert bad.height == 0
    assert damages["health_pre"].max() <= 100


def test_rounds_official_end(demo_path: Path) -> None:
    rounds = Demo(demo_path).rounds
    assert "official_end_tick" in rounds.columns


def test_bomb(demo_path: Path) -> None:
    bomb = Demo(demo_path).bomb
    assert isinstance(bomb, pl.DataFrame)
    assert {"tick", "event", "steamid", "name", "bombsite", "x", "y", "z"} <= set(bomb.columns)
    assert set(bomb["event"].unique()) <= {
        "pickup",
        "drop",
        "start_plant",
        "interrupt_plant",
        "finish_plant",
        "defuse",
    }


def test_grenades(demo_path: Path) -> None:
    g = Demo(demo_path).grenades
    assert isinstance(g, pl.DataFrame)
    assert {"tick", "thrower_name", "type", "entity_id", "x", "y", "z"} <= set(g.columns)
    # The smoke-grenade projectile is BOTH a grenade (its throw) and a smoke (its
    # cloud); its throw trajectory must still land in grenades. Guards the shared
    # projectile pass against dropping the class's second role.
    assert g.filter(pl.col("type") == "smoke").height > 0
    assert set(g["type"].unique()) <= {"smoke", "he", "flashbang", "molotov", "decoy", "grenade"}


def test_fires_and_smokes(demo_path: Path) -> None:
    demo = Demo(demo_path)
    for df in (demo.fires, demo.smokes):
        assert isinstance(df, pl.DataFrame)
        assert {
            "start_tick",
            "end_tick",
            "thrower_steamid",
            "entity_id",
            "x",
            "y",
            "z",
        } <= set(df.columns)
        assert "tick" not in df.columns  # one row per instance, not per tick
        assert df.height > 0
        # Exactly one row per (entity_id, start_tick) instance.
        assert df.height == df.select("entity_id", "start_tick").n_unique()
        # A single burn covers a positive span of ticks.
        assert (df["end_tick"] > df["start_tick"]).all()


def test_shots(demo_path: Path) -> None:
    shots = Demo(demo_path).shots
    assert isinstance(shots, pl.DataFrame)
    assert {
        "tick",
        "steamid",
        "name",
        "side",
        "x",
        "y",
        "z",
        "pitch",
        "yaw",
        "weapon",
        "scoped",
        "inaccuracy",
        "num_bullets_remaining",
    } <= set(shots.columns)
    assert shots.height > 0

    # Every shot resolves its shooter from the pawn handle.
    assert shots["steamid"].is_not_null().all()

    # Clip / accuracy come from following the shooter's active-weapon handle to a
    # weapon entity, which the shared event pass decodes via the weapon-class
    # filter. If that filter ever stops covering a fired weapon, clip/accuracy
    # silently go null — so guard the common case: firearm shots dominate
    # weapon_fire events, so the large majority of shots must resolve a clip, and
    # at least one must carry a real (positive) round count.
    clip_frac = shots["num_bullets_remaining"].is_not_null().mean()
    assert clip_frac >= 0.7, f"only {clip_frac:.1%} of shots resolved a weapon clip"
    assert shots["inaccuracy"].is_not_null().mean() >= 0.7
    assert (shots["num_bullets_remaining"] > 0).sum() > 0


def test_dataset_groups_match_fresh_parse(demo_path: Path) -> None:
    # Incremental dataset groups remain identical to independent cold parses.
    d = Demo(demo_path)
    _ = d.kills
    fresh = Demo(demo_path)
    for name in ("kills", "damages", "bomb", "shots", "grenades", "rounds", "players", "stats"):
        got = getattr(d, name)
        assert isinstance(got, pl.DataFrame)
        # Row counts are deterministic across independent parses of the same demo
        # (the parallel passes are byte-identical to serial ones).
        assert got.height == getattr(fresh, name).height, f"{name} row count differs"
    # A standard match has a full server of players and at least one round.
    assert d.players.height >= 10
    assert d.rounds.height > 0


def test_stats(demo_path: Path) -> None:
    stats = Demo(demo_path).stats
    assert isinstance(stats, pl.DataFrame)
    assert {
        "steamid",
        "name",
        "rounds_played",
        "kills",
        "deaths",
        "assists",
        "flash_assists",
        "headshot_kills",
        "opening_kills",
        "opening_deaths",
        "traded_deaths",
        "kast",
        "adr",
    } <= set(stats.columns)
    assert stats.height > 0
    # KAST is a percentage; ADR is non-negative; every opening kill has a death.
    assert stats["kast"].max() <= 100.0
    assert stats["adr"].min() >= 0.0
    assert stats["opening_kills"].sum() == stats["opening_deaths"].sum()
    # Non-negative counts throughout.
    assert stats["kills"].min() >= 0
    # Flash assists are a subset of assists (every flash assist is an assist).
    assert (stats["flash_assists"] <= stats["assists"]).all()

    # Utility stats: present, non-negative, and something happened over a match.
    assert {
        "utility_damage",
        "flashes_thrown",
        "enemies_flashed",
        "flash_duration_dealt",
    } <= set(stats.columns)
    for col in ("utility_damage", "flashes_thrown", "enemies_flashed", "flash_duration_dealt"):
        assert stats[col].min() >= 0
    assert stats["flashes_thrown"].sum() > 0
    assert stats["utility_damage"].sum() > 0
    # You can't blind more enemies than you threw flashes at (loosely).
    assert stats["flash_duration_dealt"].sum() > 0


def test_fused_stats_matches_full_datasets(demo_path: Path) -> None:
    # Stats-first uses the selective fused pass.
    fused = Demo(demo_path)
    fused_stats = fused.stats

    # A planned union of the four stats event inputs exercises aggregation
    # from independently cached parts, including fully enriched shots.
    full = Demo(demo_path)
    full.load("kills", "damages", "blinds", "shots")
    full_kills = full.kills
    full_stats = full.stats

    assert fused_stats.equals(full_stats)
    assert fused.kills.equals(full_kills)
    assert fused.damages.equals(full.damages)
    assert fused.blinds.equals(full.blinds)
    assert fused.rounds.equals(full.rounds)

    # The fused pass also tracks the roster using changed entity indices.
    assert fused.players.equals(Demo(demo_path).players)


def test_load_unions_and_caches_datasets(demo_path: Path) -> None:
    assert {"players", "stats", "rounds", "kills"} <= set(Demo.available_datasets())

    demo = Demo(demo_path)
    requested = (
        "players",
        "stats",
        "rounds",
        "kills",
        "damages",
        "blinds",
        "bomb",
        "shots",
        "grenades",
        "fires",
        "smokes",
    )
    assert demo.load(*requested) is None

    players = demo.players
    stats = demo.stats
    rounds = demo.rounds
    kills = demo.kills
    damages = demo.damages
    blinds = demo.blinds
    bomb = demo.bomb
    shots = demo.shots
    grenades = demo.grenades
    fires = demo.fires
    smokes = demo.smokes
    assert demo.players is players
    assert demo.stats is stats
    assert demo.rounds is rounds
    assert demo.kills is kills
    assert demo.damages is damages
    assert demo.blinds is blinds
    assert demo.bomb is bomb
    assert demo.shots is shots
    assert demo.grenades is grenades
    assert demo.fires is fires
    assert demo.smokes is smokes

    # Planned union rows must match incrementally selected cold datasets.
    fresh = Demo(demo_path)
    for name in ("kills", "damages", "blinds", "bomb", "shots"):
        assert getattr(demo, name).equals(getattr(fresh, name)), name
    fresh = Demo(demo_path)
    for name in ("grenades", "fires", "smokes"):
        assert getattr(demo, name).equals(getattr(fresh, name)), name

    with pytest.raises(ValueError, match="unknown dataset"):
        demo.load("not_a_dataset")


CLUTCH_COLS = ("clutch_1v1", "clutch_1v2", "clutch_1v3", "clutch_1v4", "clutch_1v5")


def test_stats_clutches(demo_path: Path) -> None:
    demo = Demo(demo_path)
    stats = demo.stats
    assert {"clutches_played", "clutches_won", *CLUTCH_COLS} <= set(stats.columns)
    for col in ("clutches_played", "clutches_won", *CLUTCH_COLS):
        assert stats[col].min() >= 0

    # You cannot win more clutches than you played.
    assert (stats["clutches_won"] <= stats["clutches_played"]).all()
    # The 1vN breakdown covers exactly the wins.
    breakdown = sum(stats[col] for col in CLUTCH_COLS)
    assert (breakdown == stats["clutches_won"]).all()

    # At most one clutch per side per round, so never more than 2 per round.
    n_rounds = demo.rounds.filter(~pl.col("is_knife_round")).height
    assert stats["clutches_played"].sum() <= 2 * n_rounds
    # A full match always leaves someone last alive at least once.
    assert stats["clutches_played"].sum() > 0


def test_kills_trade_flags(demo_path: Path) -> None:
    kills = Demo(demo_path).kills
    assert {"is_trade", "victim_traded"} <= set(kills.columns)
    assert kills["is_trade"].dtype == pl.Boolean
    assert kills["victim_traded"].dtype == pl.Boolean

    trades = kills.filter(pl.col("is_trade"))
    traded = kills.filter(pl.col("victim_traded"))
    assert trades.height > 0, "a full match always has trade kills"
    # Duals: every trade kill must be preceded by a traded death on the other
    # side, and one kill can avenge several teammates at once — so traded deaths
    # are at least as numerous as the kills that avenged them, never fewer.
    assert traded.height >= trades.height
    # A trade kill is by definition against the opposing side.
    assert (trades["attacker_side"] != trades["victim_side"]).all()
    # A death with no resolved victim side has no team to avenge it.
    assert traded["victim_side"].null_count() == 0


def test_traded_deaths_match_the_kills_dataset(demo_path: Path) -> None:
    """``stats.traded_deaths`` and ``kills.victim_traded`` share one classifier."""
    demo = Demo(demo_path)
    rounds = demo.rounds.sort("round_num")
    live = rounds.filter(~pl.col("is_knife_round"))
    per_player = (
        demo.kills.filter(pl.col("victim_traded"))
        .group_by("victim_steamid")
        .len()
        .rename({"victim_steamid": "steamid", "len": "flagged"})
    )
    joined = demo.stats.join(per_player, on="steamid", how="left").with_columns(
        pl.col("flagged").fill_null(0)
    )
    if live.height == rounds.height:
        # No knife round to exclude, so the two must agree exactly.
        assert (joined["traded_deaths"] == joined["flagged"]).all()
    else:
        # Knife-round trades are dropped from stats but still flagged on kills.
        assert (joined["traded_deaths"] <= joined["flagged"]).all()


def test_round_economy(demo_path: Path) -> None:
    econ = Demo(demo_path).round_economy
    assert isinstance(econ, pl.DataFrame)
    assert {"round_num", "side", "equipment_value", "buy_type", "n_players"} <= set(econ.columns)
    assert econ.height > 0
    # One row per (round, side).
    assert econ.select("round_num", "side").n_unique() == econ.height
    assert set(econ["side"].unique()) <= {"terrorist", "counter-terrorist"}
    assert set(econ["buy_type"].unique()) <= {"pistol", "eco", "force", "full"}
    # Team equipment is non-negative, and a real match has a mix of buy types.
    assert econ["equipment_value"].min() >= 0
    assert econ["buy_type"].n_unique() >= 2
    # Round 1 is a pistol round for both teams (detected via the halftime side
    # flip, so there is a second pistol round later too).
    assert (econ.filter(pl.col("round_num") == 1)["buy_type"] == "pistol").all()
    pistol_rounds = econ.filter(pl.col("buy_type") == "pistol")["round_num"].unique()
    assert len(pistol_rounds) == 2  # round 1 and the second-half pistol


def test_schema_constants() -> None:
    from awpy import GAME_EVENTS, SNAPSHOT_PROPERTIES

    assert isinstance(SNAPSHOT_PROPERTIES, dict) and SNAPSHOT_PROPERTIES
    assert isinstance(GAME_EVENTS, dict) and "player_death" in GAME_EVENTS
    # Values map to engine property names / descriptions (all strings).
    assert all(isinstance(v, str) for v in SNAPSHOT_PROPERTIES.values())


def test_snapshot_properties_match_schema(demo_path: Path) -> None:
    # The SNAPSHOT_PROPERTIES catalog must stay in sync with what snapshot() emits.
    from awpy import SNAPSHOT_PROPERTIES

    tick = Demo(demo_path).rounds.row(1, named=True)["freeze_end_tick"]
    cols = set(Demo(demo_path).snapshots(ticks=tick).columns) - {"tick"}
    assert cols == set(SNAPSHOT_PROPERTIES)
