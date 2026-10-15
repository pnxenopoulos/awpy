"""Tests for the awpy Python bindings.

Tests that need demos use the fixtures marker (see conftest).
The error-handling tests do not need demo files.
"""

from pathlib import Path

import polars as pl
import pytest
from awpy import SNAPSHOT_PROPERTIES, Demo, InvalidDemoError
from polars.testing import assert_frame_equal


@pytest.fixture(scope="module")
def default_ticks(demo: Demo) -> pl.DataFrame:
    return demo.ticks()


@pytest.fixture(scope="module")
def named_ticks(demo: Demo) -> pl.DataFrame:
    return demo.ticks(["m_iTeamNum", "name", "velocity_x", "velocity"])


@pytest.fixture(scope="module")
def entity_ticks(demo: Demo) -> pl.DataFrame:
    return demo.ticks(["m_iTeamNum"], players_only=False)


@pytest.fixture(scope="module")
def first_snapshot(demo: Demo) -> pl.DataFrame:
    return demo.snapshots(ticks=demo.rounds["freeze_end_tick"][0])


@pytest.fixture(scope="module")
def sampled_snapshots(demo: Demo) -> pl.DataFrame:
    return demo.snapshots(every=256)


BATCH_DATASETS = (
    "kills",
    "damages",
    "blinds",
    "bomb",
    "shots",
    "grenades",
    "fires",
    "smokes",
    "rounds",
    "players",
    "stats",
)


@pytest.fixture(scope="module")
def grouped_load(demo_path: Path) -> tuple[Demo, None]:
    parsed = Demo(demo_path)
    result = parsed.load(*BATCH_DATASETS)
    return parsed, result


@pytest.fixture(scope="module")
def combat_demo(demo_path: Path) -> Demo:
    parsed = Demo(demo_path)
    parsed.load("kills", "damages", "blinds", "shots")
    return parsed


@pytest.fixture(scope="module")
def fused_demo(demo_path: Path) -> Demo:
    parsed = Demo(demo_path)
    _ = parsed.stats
    return parsed


def test_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        Demo("does-not-exist.dem")


def test_invalid_file_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.dem"
    bogus.write_bytes(b"not a demo file at all")
    with pytest.raises(InvalidDemoError):
        Demo(bogus)


def test_header(demo: Demo) -> None:
    header = demo.header
    assert isinstance(header, dict)
    assert "map_name" in header
    assert header["map_name"].startswith("de_")


def test_event_names_are_sorted_and_iterable(demo: Demo) -> None:
    events = demo.events
    assert "player_death" in events
    assert "player_death" in events.names
    assert list(events) == events.names == sorted(events.names)
    assert len(events) == len(events.names)


def test_event_counts_include_recorded_deaths(demo: Demo) -> None:
    events = demo.events
    assert events.counts["player_death"] > 0


def test_event_repr_lists_known_names(demo: Demo) -> None:
    events = demo.events
    assert "player_death" in repr(events)


def test_death_events_have_recorded_columns(demo: Demo) -> None:
    deaths = demo.events.player_death
    assert isinstance(deaths, pl.DataFrame)
    assert "tick" in deaths.columns
    assert "attacker" in deaths.columns
    assert deaths.height > 0


def test_event_item_access_reuses_the_attribute_frame(demo: Demo) -> None:
    deaths = demo.events.player_death
    assert demo.events["player_death"] is deaths


def test_event_accessor_is_cached(demo: Demo) -> None:
    assert demo.events is demo.events


def test_unknown_event_item_raises_key_error(demo: Demo) -> None:
    events = demo.events
    with pytest.raises(KeyError, match="no_such_event"):
        events["no_such_event"]


def test_unknown_event_attribute_raises_attribute_error(demo: Demo) -> None:
    events = demo.events
    with pytest.raises(AttributeError, match="no_such_event"):
        _ = events.no_such_event


def test_default_ticks_have_core_schema(default_ticks: pl.DataFrame) -> None:
    ticks = default_ticks
    assert isinstance(ticks, pl.DataFrame)
    assert {"tick", "steamid", "X", "Y", "Z", "health", "armor", "team_num"} <= set(ticks.columns)
    assert ticks["steamid"].dtype == pl.UInt64
    assert ticks.height > 0


def test_tick_identity_is_complete_and_unique(default_ticks: pl.DataFrame) -> None:
    ticks = default_ticks
    assert ticks["steamid"].is_null().sum() == 0
    assert ticks.select(["tick", "steamid"]).n_unique() == ticks.height


def test_ticks_cover_the_match_roster(default_ticks: pl.DataFrame) -> None:
    ticks = default_ticks
    per_tick = ticks.group_by("tick").len()["len"]
    assert per_tick.max() <= 12  # 10 players (+ occasional connecting/GOTV)
    assert per_tick.median() >= 8


def test_tick_positions_use_world_coordinates(default_ticks: pl.DataFrame) -> None:
    ticks = default_ticks
    assert ticks["X"].abs().max() > 100.0


def test_tick_health_stays_in_the_player_range(default_ticks: pl.DataFrame) -> None:
    ticks = default_ticks
    assert 0 <= ticks["health"].min() and ticks["health"].max() <= 100


def test_tick_aliases_resolve_pawn_and_controller_fields(named_ticks: pl.DataFrame) -> None:
    named = named_ticks
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


def test_raw_ticks_keep_separate_entity_identities(
    entity_ticks: pl.DataFrame, default_ticks: pl.DataFrame
) -> None:
    raw, ticks = entity_ticks, default_ticks
    assert {
        "tick",
        "entity_id",
        "entity_serial",
        "class_name",
        "m_iTeamNum",
    } <= set(raw.columns)
    assert raw.height > ticks.height


@pytest.mark.parametrize(
    ("method", "options"),
    [("ticks", {}), ("snapshots", {"every": 64})],
    ids=["ticks", "snapshots"],
)
def test_parallel_matches_serial(
    demo_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, options: dict[str, int]
) -> None:
    """Check both decode paths with one and eight segments."""
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "1")
    serial = getattr(Demo(demo_path), method)(**options)
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", "8")
    parallel = getattr(Demo(demo_path), method)(**options)
    keys = ["tick", "steamid"]
    assert_frame_equal(serial.sort(keys), parallel.sort(keys), check_exact=True)


def test_players(demo: Demo) -> None:
    players = demo.players
    assert isinstance(players, pl.DataFrame)
    assert {"steamid", "name", "side", "team_clan_name"} <= set(players.columns)
    humans = players.filter(pl.col("steamid") > 0)
    assert humans.height == 10
    assert humans["steamid"].n_unique() == 10
    assert set(humans["side"].unique()) <= {"terrorist", "counter-terrorist"}


def test_playing_sides_have_consistent_clan_names(demo: Demo) -> None:
    players = demo.players
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


def test_spectators_have_no_clan_name(demo: Demo) -> None:
    players = demo.players
    bench = players.filter(~pl.col("side").is_in(["terrorist", "counter-terrorist"]))
    assert bench["team_clan_name"].null_count() == bench.height


def test_tick_rate_matches_recorded_playback(demo: Demo) -> None:
    assert isinstance(demo.tick_rate, float)
    # Every competitive demo is 64 or 128 tick; the fallback is 64.
    assert demo.tick_rate in (64.0, 128.0)
    # Consistent with the header's own playback timing, when it reports it.
    header = demo.header
    ticks, seconds = header.get("playback_ticks"), header.get("playback_time")
    if ticks and seconds:
        assert demo.tick_rate == pytest.approx(ticks / seconds, rel=1e-3)


def test_tick_to_seconds_uses_the_tick_rate(demo: Demo) -> None:
    tick = 12_345
    elapsed = demo.tick_to_seconds(tick)
    assert elapsed == pytest.approx(tick / demo.tick_rate)


def test_seconds_to_tick_round_trips_ticks(demo: Demo) -> None:
    tick = 12_345
    elapsed = demo.tick_to_seconds(tick)
    assert demo.seconds_to_tick(elapsed) == tick


def test_seconds_to_tick_accepts_negative_time(demo: Demo) -> None:
    assert demo.seconds_to_tick(-1.0) == -round(demo.tick_rate)


def test_seconds_to_tick_rejects_infinity(demo: Demo) -> None:
    with pytest.raises(ValueError):
        demo.seconds_to_tick(float("inf"))


def test_seconds_to_tick_rejects_nan(demo: Demo) -> None:
    with pytest.raises(ValueError):
        demo.seconds_to_tick(float("nan"))


def test_snapshot_schema_matches_the_property_catalog(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
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
    assert set(snap.columns) == {"tick", *SNAPSHOT_PROPERTIES}
    for name in ("is_reloading", "is_silent_reloading"):
        assert snap[name].dtype == pl.Boolean


def test_single_snapshot_contains_all_players_at_the_selected_tick(
    demo: Demo, first_snapshot: pl.DataFrame
) -> None:
    snap = first_snapshot
    tick = demo.rounds["freeze_end_tick"][0]
    assert snap.height == 10  # every player, alive at freeze end
    assert snap["tick"].unique().to_list() == [tick]


def test_freeze_end_players_have_full_health(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["health"].min() == 100


def test_snapshot_positions_are_resolved(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["x"].null_count() == 0


def test_snapshot_velocity_is_resolved_and_nonnegative(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["velocity_x"].null_count() == 0
    assert snap["velocity"].min() >= 0


def test_empty_snapshot_selection_keeps_reload_schema(demo: Demo) -> None:
    empty = demo.snapshots(ticks=[2_000_000_000, 2_000_000_001])
    assert empty.is_empty()
    for name in ("is_reloading", "is_silent_reloading"):
        assert empty[name].dtype == pl.Boolean


def test_single_seeks_work_away_from_full_packets(demo: Demo) -> None:
    for probe in (2000, 29000, 60000, 150000):
        assert demo.snapshots(ticks=probe).height == 10, f"empty snapshot at tick {probe}"


def test_snapshot_tick_range(demo: Demo) -> None:
    start = demo.rounds.row(0, named=True)["freeze_end_tick"]
    span = demo.snapshots(start_tick=start, end_tick=start + 128)
    ticks = span["tick"]
    assert ticks.min() >= start and ticks.max() <= start + 128
    assert ticks.n_unique() > 1
    assert span.height == ticks.n_unique() * 10


def test_sampled_snapshot_schema_matches_single_seeks(
    demo: Demo, sampled_snapshots: pl.DataFrame
) -> None:
    every = sampled_snapshots
    one = demo.snapshots(ticks=demo.rounds["freeze_end_tick"][0])
    assert set(every.columns) == set(one.columns)


def test_snapshot_stride_keeps_even_tick_spacing(sampled_snapshots: pl.DataFrame) -> None:
    every = sampled_snapshots
    gaps = every["tick"].unique().sort().diff().drop_nulls()
    assert gaps.min() >= 256 and gaps.max() == 256  # gap-robust stride hits exactly N


def test_sampled_snapshots_keep_the_full_roster(sampled_snapshots: pl.DataFrame) -> None:
    every = sampled_snapshots
    assert every.height == every["tick"].n_unique() * 10


def test_sampled_snapshots_resolve_weapon_entities(sampled_snapshots: pl.DataFrame) -> None:
    every = sampled_snapshots
    assert every["primary_weapon"].drop_nulls().len() > 0
    assert every.filter(pl.col("inventory") != "").height > 0


def test_seconds_sampling_converts_to_a_tick_stride(demo: Demo) -> None:
    per_sec = demo.snapshots(seconds=4.0)
    assert per_sec["tick"].unique().sort().diff().drop_nulls().max() == 256


def test_death_sampling_uses_exact_event_ticks(demo: Demo) -> None:
    kill_ticks = set(demo.kills["tick"].to_list())
    on_kills = demo.snapshots(events="player_death")
    assert set(on_kills["tick"].to_list()) == kill_ticks


def test_multiple_event_selectors_form_a_tick_union(demo: Demo) -> None:
    kill_ticks = set(demo.kills["tick"].to_list())
    plant_ticks = set(demo.bomb.filter(pl.col("event") == "finish_plant")["tick"].to_list())
    on_kills_or_plants = demo.snapshots(events=["player_death", "bomb_planted"])
    assert set(on_kills_or_plants["tick"].to_list()) == kill_ticks | plant_ticks


def test_explicit_snapshot_selection_uses_only_requested_ticks(
    demo: Demo, sampled_snapshots: pl.DataFrame
) -> None:
    every = sampled_snapshots
    some_ticks = every["tick"].unique().to_list()[:3]
    picked = demo.snapshots(ticks=some_ticks)
    assert set(picked["tick"].to_list()) == set(some_ticks)


def test_stride_and_event_selectors_form_a_tick_union(
    demo: Demo, sampled_snapshots: pl.DataFrame
) -> None:
    every = sampled_snapshots
    kill_ticks = set(demo.kills["tick"].to_list())
    union = demo.snapshots(every=256, events="player_death")
    assert kill_ticks <= set(union["tick"].to_list())
    assert set(every["tick"].to_list()) <= set(union["tick"].to_list())


@pytest.mark.parametrize("window", [{}, {"start_tick": 0, "end_tick": 1000}])
def test_snapshot_event_selection_without_matches_returns_empty(demo: Demo, window: dict) -> None:
    frame = demo.snapshots(events="__awpy_missing_event__", **window)
    assert frame.is_empty()
    assert frame.schema["inventory"] == pl.String


def test_snapshots_require_a_selector(demo: Demo) -> None:
    with pytest.raises(ValueError):
        demo.snapshots()


def test_snapshot_time_and_tick_strides_are_mutually_exclusive(demo: Demo) -> None:
    with pytest.raises(ValueError):
        demo.snapshots(every=64, seconds=1.0)


def test_snapshot_economy_schema(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
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
        "is_blinded",
        "flash_duration",
        "inventory",
    }
    assert econ <= set(snap.columns)
    assert snap["equipment_value"].dtype == pl.Int32


def test_freeze_end_equipment_has_positive_value(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert (snap["equipment_value"] > 0).all()


def test_freeze_end_loadouts_include_a_knife(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["inventory"].str.contains("knife").all()


def test_pistol_round_loadouts_have_pistols_and_no_primary_weapon(
    first_snapshot: pl.DataFrame,
) -> None:
    snap = first_snapshot
    assert snap["secondary_weapon"].null_count() == 0
    assert snap["primary_weapon"].null_count() == 10


def test_one_player_carries_the_bomb_at_freeze_end(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["has_bomb"].sum() == 1


def test_snapshot_money_is_nonnegative(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["money"].min() >= 0


def test_snapshot_active_weapons_are_resolved(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert snap["active_weapon"].null_count() == 0


def test_snapshot_grenade_counts_are_nonnegative(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    for col in ("he_grenades", "flashbangs", "smoke_grenades", "fire_grenades", "decoy_grenades"):
        assert snap[col].min() >= 0


def test_loadouts_do_not_repeat_the_bomb(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    assert (snap["inventory"].str.count_matches("c4") <= 1).all()


def test_secondary_weapon_names_match_the_inventory(first_snapshot: pl.DataFrame) -> None:
    snap = first_snapshot
    for row in snap.iter_rows(named=True):
        if row["secondary_weapon"]:
            assert row["secondary_weapon"] in row["inventory"]


def test_blinds_schema(demo: Demo) -> None:
    blinds = demo.blinds
    assert isinstance(blinds, pl.DataFrame)
    expected = {
        "tick",
        "attacker_entity_id",
        "attacker_entity_serial",
        "victim_entity_id",
        "victim_entity_serial",
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
    assert blinds["victim_entity_serial"].dtype == pl.UInt32


def test_blind_duration_stays_within_the_flash_limit(demo: Demo) -> None:
    blinds = demo.blinds
    assert (blinds["duration"] > 0).all()
    assert blinds["duration"].max() <= 6.0  # engine flash cap is ~5 s


def test_blind_victim_identity_is_resolved(demo: Demo) -> None:
    blinds = demo.blinds
    assert blinds["victim_side"].null_count() == 0
    assert set(blinds["victim_side"].unique()) <= {"terrorist", "counter-terrorist"}
    assert blinds["victim_x"].null_count() == 0
    assert blinds["victim_entity_id"].null_count() == 0


def test_blinds_are_in_tick_order(demo: Demo) -> None:
    blinds = demo.blinds
    assert blinds["tick"].to_list() == sorted(blinds["tick"].to_list())


def test_item_event_schema(demo: Demo) -> None:
    items = demo.item_events
    assert isinstance(items, pl.DataFrame)
    expected = {
        "tick",
        "action",
        "entity_id",
        "entity_serial",
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
    assert items["entity_id"].null_count() == 0
    assert items["entity_serial"].dtype == pl.UInt32


def test_item_events_exclude_default_knives(demo: Demo) -> None:
    items = demo.item_events
    assert "knife" not in set(items["item"].unique())


def test_item_events_are_in_tick_order(demo: Demo) -> None:
    items = demo.item_events
    assert items["tick"].to_list() == sorted(items["tick"].to_list())


def test_purchases_record_the_buyers_own_weapon(demo: Demo) -> None:
    items = demo.item_events
    purchases = items.filter(pl.col("action") == "purchase")
    assert purchases.height > 0
    # A purchase is the buyer's own weapon, at a plausible cost (never a money
    # reset, which would show as a huge "cost").
    assert (purchases["original_owner_steamid"] == purchases["steamid"]).all()


def test_purchase_costs_stay_in_the_item_price_range(demo: Demo) -> None:
    purchases = demo.item_events.filter(pl.col("action") == "purchase")
    assert purchases["cost"].min() > 0
    assert purchases["cost"].max() <= 6500


def test_pickups_and_drops_have_no_purchase_cost(demo: Demo) -> None:
    items = demo.item_events
    non_purchase = items.filter(pl.col("action") != "purchase")
    assert non_purchase["cost"].null_count() == non_purchase.height


def test_drops_record_buy_zone_state(demo: Demo) -> None:
    items = demo.item_events
    drops = items.filter(pl.col("action") == "drop")
    if drops.height:
        assert drops["near_buy_zone"].null_count() == 0


def test_nullable_steamid_columns_use_uint64(demo: Demo) -> None:
    """Steam IDs do not become floats when values are null."""
    frames = (
        demo.kills,
        demo.damages,
        demo.bomb,
        demo.grenades,
        demo.fires,
        demo.smokes,
        demo.shots,
        demo.blinds,
        demo.item_events,
    )

    for frame in frames:
        steamid_columns = [name for name in frame.columns if name.endswith("steamid")]
        assert steamid_columns
        assert all(frame.schema[name] == pl.UInt64 for name in steamid_columns)


def test_chat_schema(demo: Demo) -> None:
    chat = demo.chat
    assert isinstance(chat, pl.DataFrame)
    # Server-side demos may strip chat entirely; the schema must hold anyway.
    assert {"tick", "entity_index", "name", "message", "channel"} <= set(chat.columns)


def test_chat_includes_each_saytext_message(demo: Demo) -> None:
    chat = demo.chat
    say_text_count = sum(
        count for name, count in demo.events.counts.items() if "saytext" in name.lower()
    )
    assert chat.height == say_text_count


def test_chat_text_is_not_null(demo: Demo) -> None:
    chat = demo.chat
    assert chat["message"].null_count() == 0


def test_convars(demo: Demo) -> None:
    convars = demo.convars
    assert isinstance(convars, dict)
    assert convars  # every demo carries at least the signon convars
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in convars.items())
    assert any(key.startswith("mp_") for key in convars)


def test_round_schema(demo: Demo) -> None:
    rounds = demo.rounds
    assert isinstance(rounds, pl.DataFrame)
    assert {
        "round_num",
        "start_tick",
        "freeze_end_tick",
        "end_tick",
        "official_end_tick",
        "winner",
        "winner_side",
        "reason_name",
    } <= set(rounds.columns)
    assert rounds.height > 0


def test_round_winners_are_playing_sides(demo: Demo) -> None:
    rounds = demo.rounds
    assert set(rounds["winner_side"].unique()) <= {"terrorist", "counter-terrorist"}


def test_round_end_ticks_are_ordered(demo: Demo) -> None:
    rounds = demo.rounds
    end = rounds["end_tick"].to_list()
    assert end == sorted(end)


def test_kill_schema(demo: Demo) -> None:
    kills = demo.kills
    assert isinstance(kills, pl.DataFrame)
    expected = {
        "attacker_steamid",
        "attacker_entity_id",
        "attacker_entity_serial",
        "victim_entity_id",
        "victim_entity_serial",
        "assister_entity_id",
        "assister_entity_serial",
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
    assert kills["victim_entity_serial"].dtype == pl.UInt32


def test_kill_victims_have_entity_identity(demo: Demo) -> None:
    kills = demo.kills
    assert kills["victim_entity_id"].null_count() == 0


def test_resolved_kill_attackers_have_entity_identity(demo: Demo) -> None:
    kills = demo.kills
    assert (
        kills.filter(pl.col("attacker_steamid").is_not_null())["attacker_entity_id"]
        .is_not_null()
        .all()
    )


def test_kill_attackers_have_playing_sides_when_present(demo: Demo) -> None:
    kills = demo.kills
    sides = set(kills["attacker_side"].drop_nulls().unique())
    assert sides <= {"terrorist", "counter-terrorist"}


def test_damage_schema(demo: Demo) -> None:
    damages = demo.damages
    assert isinstance(damages, pl.DataFrame)
    assert {
        "attacker_name",
        "victim_name",
        "weapon",
        "attacker_entity_id",
        "attacker_entity_serial",
        "victim_entity_id",
        "victim_entity_serial",
        "dmg_health",
        "hitgroup_name",
        "health_pre",
        "health_post",
        "armor_pre",
        "armor_post",
        "tick",
    } <= set(damages.columns)
    assert damages.height > 0
    assert damages["victim_entity_serial"].dtype == pl.UInt32


def test_damage_pre_health_is_reconstructed_and_capped(demo: Demo) -> None:
    damages = demo.damages
    bad = damages.filter(
        pl.col("health_pre")
        != pl.min_horizontal(pl.col("health_post") + pl.col("dmg_health"), pl.lit(100))
    )
    assert bad.height == 0
    assert damages["health_pre"].max() <= 100


def test_damage_victims_have_entity_identity(demo: Demo) -> None:
    damages = demo.damages
    assert damages["victim_entity_id"].null_count() == 0


def test_bomb(demo: Demo) -> None:
    bomb = demo.bomb
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
    assert {"entity_id", "entity_serial"} <= set(bomb.columns)


def test_grenade_schema(demo: Demo) -> None:
    g = demo.grenades
    assert isinstance(g, pl.DataFrame)
    assert {"tick", "thrower_name", "type", "entity_id", "x", "y", "z"} <= set(g.columns)
    assert "entity_serial" in g.columns
    assert g["entity_serial"].dtype == pl.UInt32


def test_smoke_projectiles_keep_their_grenade_role(demo: Demo) -> None:
    g = demo.grenades
    assert g.filter(pl.col("type") == "smoke").height > 0


def test_grenades_use_known_type_labels(demo: Demo) -> None:
    g = demo.grenades
    assert set(g["type"].unique()) <= {"smoke", "he", "flashbang", "molotov", "decoy", "grenade"}


def test_fires_and_smokes(demo: Demo) -> None:
    for df in (demo.fires, demo.smokes):
        assert isinstance(df, pl.DataFrame)
        assert {
            "start_tick",
            "end_tick",
            "thrower_steamid",
            "entity_id",
            "entity_serial",
            "x",
            "y",
            "z",
        } <= set(df.columns)
        assert "tick" not in df.columns  # one row per instance, not per tick
        assert df.height > 0
        # Exactly one row per (entity_id, start_tick) instance.
        assert df.height == df.select("entity_id", "entity_serial", "start_tick").n_unique()
        # A single burn covers a positive span of ticks.
        assert (df["end_tick"] > df["start_tick"]).all()


def test_shot_schema(demo: Demo) -> None:
    shots = demo.shots
    assert isinstance(shots, pl.DataFrame)
    assert {
        "tick",
        "steamid",
        "name",
        "side",
        "x",
        "entity_id",
        "entity_serial",
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
    assert shots["entity_serial"].dtype == pl.UInt32


def test_shot_identity_is_resolved(demo: Demo) -> None:
    shots = demo.shots
    assert shots["steamid"].is_not_null().all()
    assert shots["entity_id"].is_not_null().all()


def test_shots_resolve_recorded_clip_counts(demo: Demo) -> None:
    shots = demo.shots
    clip_frac = shots["num_bullets_remaining"].is_not_null().mean()
    assert clip_frac >= 0.7, f"only {clip_frac:.1%} of shots resolved a weapon clip"
    assert (shots["num_bullets_remaining"] > 0).sum() > 0


def test_shots_resolve_weapon_inaccuracy(demo: Demo) -> None:
    shots = demo.shots
    assert shots["inaccuracy"].is_not_null().mean() >= 0.7


def test_scoreboard_schema(demo: Demo) -> None:
    stats = demo.stats
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
    assert {
        "utility_damage",
        "flashes_thrown",
        "enemies_flashed",
        "flash_duration_dealt",
    } <= set(stats.columns)


def test_kast_is_a_percentage(demo: Demo) -> None:
    stats = demo.stats
    assert stats["kast"].max() <= 100.0


def test_adr_is_nonnegative(demo: Demo) -> None:
    stats = demo.stats
    assert stats["adr"].min() >= 0.0


def test_opening_kill_and_death_totals_match(demo: Demo) -> None:
    stats = demo.stats
    assert stats["opening_kills"].sum() == stats["opening_deaths"].sum()


def test_kill_counts_are_nonnegative(demo: Demo) -> None:
    stats = demo.stats
    assert stats["kills"].min() >= 0


def test_stats_property_reuses_the_default_method_result(demo: Demo) -> None:
    stats = demo.stats
    assert stats is demo.player_stats()


def test_stats_including_knife_rounds_are_cached(demo: Demo) -> None:
    with_knife_rounds = demo.player_stats(include_knife_rounds=True)
    assert with_knife_rounds is demo.player_stats(include_knife_rounds=True)


def test_flash_assists_are_a_subset_of_assists(demo: Demo) -> None:
    stats = demo.stats
    assert (stats["flash_assists"] <= stats["assists"]).all()


def test_utility_counts_are_nonnegative(demo: Demo) -> None:
    stats = demo.stats
    for col in ("utility_damage", "flashes_thrown", "enemies_flashed", "flash_duration_dealt"):
        assert stats[col].min() >= 0


def test_scoreboard_counts_recorded_flashes(demo: Demo) -> None:
    stats = demo.stats
    assert stats["flashes_thrown"].sum() > 0


def test_scoreboard_counts_utility_damage(demo: Demo) -> None:
    stats = demo.stats
    assert stats["utility_damage"].sum() > 0


def test_scoreboard_counts_blind_duration(demo: Demo) -> None:
    stats = demo.stats
    assert stats["flash_duration_dealt"].sum() > 0


CLUTCH_COLS = ("clutch_1v1", "clutch_1v2", "clutch_1v3", "clutch_1v4", "clutch_1v5")


def test_clutch_schema_and_nonnegative_counts(demo: Demo) -> None:
    stats = demo.stats
    assert {"clutches_played", "clutches_won", *CLUTCH_COLS} <= set(stats.columns)
    for col in ("clutches_played", "clutches_won", *CLUTCH_COLS):
        assert stats[col].min() >= 0


def test_clutch_wins_do_not_exceed_attempts(demo: Demo) -> None:
    stats = demo.stats
    assert (stats["clutches_won"] <= stats["clutches_played"]).all()


def test_clutch_size_breakdown_covers_each_win(demo: Demo) -> None:
    stats = demo.stats
    breakdown = sum(stats[col] for col in CLUTCH_COLS)
    assert (breakdown == stats["clutches_won"]).all()


def test_clutch_attempts_are_bounded_per_round(demo: Demo) -> None:
    stats = demo.stats
    n_rounds = demo.rounds.filter(~pl.col("is_knife_round")).height
    assert stats["clutches_played"].sum() <= 2 * n_rounds


def test_scoreboard_records_clutch_attempts(demo: Demo) -> None:
    stats = demo.stats
    assert stats["clutches_played"].sum() > 0


def test_trade_flag_schema(demo: Demo) -> None:
    kills = demo.kills
    assert {"is_trade", "victim_traded"} <= set(kills.columns)
    assert kills["is_trade"].dtype == pl.Boolean
    assert kills["victim_traded"].dtype == pl.Boolean


def test_each_trade_kill_matches_one_death(demo: Demo) -> None:
    kills = demo.kills
    trades = kills.filter(pl.col("is_trade"))
    traded = kills.filter(pl.col("victim_traded"))
    assert trades.height > 0, "a full match always has trade kills"
    # Each trade kill matches one earlier death, so the flag totals are equal.
    assert traded.height == trades.height


def test_trade_kills_are_against_opponents(demo: Demo) -> None:
    trades = demo.kills.filter(pl.col("is_trade"))
    assert (trades["attacker_side"] != trades["victim_side"]).all()


def test_traded_deaths_have_a_resolved_side(demo: Demo) -> None:
    traded = demo.kills.filter(pl.col("victim_traded"))
    assert traded["victim_side"].null_count() == 0


def test_traded_deaths_match_the_kills_dataset(demo: Demo) -> None:
    """``stats.traded_deaths`` and ``kills.victim_traded`` share one classifier."""
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


def test_round_economy_schema(demo: Demo) -> None:
    econ = demo.round_economy
    assert isinstance(econ, pl.DataFrame)
    assert {"round_num", "side", "equipment_value", "buy_type", "n_players"} <= set(econ.columns)
    assert econ.height > 0


def test_round_economy_has_one_row_per_side(demo: Demo) -> None:
    econ = demo.round_economy
    assert econ.select("round_num", "side").n_unique() == econ.height


def test_round_economy_uses_known_categories(demo: Demo) -> None:
    econ = demo.round_economy
    assert set(econ["side"].unique()) <= {"terrorist", "counter-terrorist"}
    assert set(econ["buy_type"].unique()) <= {"pistol", "eco", "force", "full"}


def test_round_equipment_values_are_nonnegative(demo: Demo) -> None:
    econ = demo.round_economy
    assert econ["equipment_value"].min() >= 0


def test_match_economy_contains_different_buy_types(demo: Demo) -> None:
    econ = demo.round_economy
    assert econ["buy_type"].n_unique() >= 2


def test_both_halves_start_with_pistol_buys(demo: Demo) -> None:
    econ = demo.round_economy
    assert (econ.filter(pl.col("round_num") == 1)["buy_type"] == "pistol").all()
    pistol_rounds = econ.filter(pl.col("buy_type") == "pistol")["round_num"].unique()
    assert len(pistol_rounds) == 2  # round 1 and the second-half pistol


def test_schema_constants() -> None:
    from awpy import GAME_EVENTS

    assert isinstance(SNAPSHOT_PROPERTIES, dict) and SNAPSHOT_PROPERTIES
    assert isinstance(GAME_EVENTS, dict) and "player_death" in GAME_EVENTS
    # Values map to engine property names / descriptions (all strings).
    assert all(isinstance(v, str) for v in SNAPSHOT_PROPERTIES.values())


@pytest.mark.fixtures
@pytest.mark.parametrize("segments", [1, 4])
@pytest.mark.parametrize(
    "match_demo",
    ["valve-de_mirage-472514809", "faceit-de_mirage-6de46e85", "hltv-de_mirage-2394170"],
    indirect=True,
)
def test_sparse_snapshots_match_full_scan(
    match_demo: Demo, segments: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWPY_TICK_SEGMENTS", str(segments))
    end = match_demo.header["playback_ticks"]
    queries = [
        [end // 3, end * 2 // 3],
        [end * i // 5 for i in range(1, 5)],
        [end // 2, end // 3, end // 2],
        [-2_000_000_000, -1, 0, 1],
        [1919, 1920, 1921],
        [2_000_000_000, 2_000_000_001],
    ]
    ticks = sorted({tick for query in queries for tick in query})
    # A window forces the scan path, even when a query has few ticks.
    reference = match_demo.snapshots(ticks=ticks, start_tick=-2_000_000_000, end_tick=2_000_000_001)
    assert reference.height > 0
    for query in queries:
        expected = reference.filter(pl.col("tick").is_in(query))
        actual = match_demo.snapshots(ticks=query)
        assert_frame_equal(actual, expected, check_exact=True)


@pytest.mark.parametrize("dataset", ["stats", "kills", "damages", "blinds", "rounds", "players"])
def test_fused_pass_matches_separately_loaded_inputs(
    fused_demo: Demo, combat_demo: Demo, dataset: str
) -> None:
    assert_frame_equal(
        getattr(fused_demo, dataset), getattr(combat_demo, dataset), check_exact=True
    )


@pytest.mark.parametrize("dataset", BATCH_DATASETS)
def test_grouped_load_matches_incremental_loads(
    grouped_load: tuple[Demo, None], demo: Demo, dataset: str
) -> None:
    assert_frame_equal(getattr(grouped_load[0], dataset), getattr(demo, dataset), check_exact=True)


@pytest.mark.parametrize("dataset", BATCH_DATASETS)
def test_loaded_dataset_is_cached(grouped_load: tuple[Demo, None], dataset: str) -> None:
    parsed = grouped_load[0]
    assert getattr(parsed, dataset) is getattr(parsed, dataset)


def test_load_returns_none(grouped_load: tuple[Demo, None]) -> None:
    assert grouped_load[1] is None


def test_available_datasets_include_the_core_tables() -> None:
    assert {"players", "stats", "rounds", "kills"} <= set(Demo.available_datasets())


def test_load_rejects_unknown_datasets(demo_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown dataset"):
        Demo(demo_path).load("not_a_dataset")
