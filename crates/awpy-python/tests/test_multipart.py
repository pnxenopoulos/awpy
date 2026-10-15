"""Native multipart inputs, recording identity, and combined queries."""

from pathlib import Path
from types import SimpleNamespace
from weakref import ref

import polars as pl
import pytest
from awpy import Demo, _awpy
from polars.testing import assert_frame_equal


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    """A valid empty header is sufficient for checks that must not decode."""
    path = tmp_path / "single.dem"
    path.write_bytes(b"PBDEMS2\0" + bytes(8))
    return path


def test_demo_is_the_native_class() -> None:
    assert Demo is _awpy.Demo


@pytest.mark.parametrize("form", [str, Path, lambda p: [str(p)], lambda p: (p,)])
def test_paths_are_coerced_to_path_objects(source_file: Path, form) -> None:
    assert Demo(form(source_file)).paths == (source_file,)


@pytest.mark.parametrize("source", [[], ()])
def test_empty_sequences_are_rejected(source: object) -> None:
    with pytest.raises(ValueError, match="at least one"):
        Demo(source)


@pytest.mark.parametrize("source", [1, b"file.dem", {"file.dem"}, iter(["file.dem"])])
def test_non_path_inputs_are_rejected(source: object) -> None:
    with pytest.raises(TypeError):
        Demo(source)


def test_repeated_paths_are_rejected_before_opening_files() -> None:
    with pytest.raises(ValueError, match="must not repeat"):
        Demo(["missing.dem", "./missing.dem"])


def test_single_file_is_its_own_only_part(source_file: Path) -> None:
    parsed = Demo(source_file)
    assert parsed.parts == (parsed,)


def test_reading_parts_does_not_retain_the_demo(source_file: Path) -> None:
    parsed = Demo(source_file)
    assert parsed.parts[0] is parsed
    reference = ref(parsed)
    del parsed
    assert reference() is None


@pytest.mark.parametrize("part", [-1, 1])
def test_invalid_part_indices_are_rejected_before_decoding(source_file: Path, part: int) -> None:
    with pytest.raises(ValueError, match="part must"):
        Demo(source_file).snapshots(part=part, ticks=10)


def test_unknown_load_datasets_fail_before_decoding(source_file: Path) -> None:
    with pytest.raises(ValueError, match="unknown dataset"):
        Demo(source_file).load("kills", "missing")


@pytest.fixture(scope="module")
def multipart() -> Demo:
    """Use the local Overpass pair without downloading or reopening it per test."""
    root = Path(__file__).resolve().parents[3]
    paths = [root / f"apeks-vs-gamerlegion-m2-overpass-p{i}.dem" for i in (1, 2)]
    if not all(path.is_file() for path in paths):
        pytest.skip("local Overpass multipart recordings are unavailable")
    return Demo([str(paths[0]), paths[1]])


def test_mixed_path_sequences_keep_the_supplied_order(multipart: Demo) -> None:
    assert [path.name for path in multipart.paths] == [
        "apeks-vs-gamerlegion-m2-overpass-p1.dem",
        "apeks-vs-gamerlegion-m2-overpass-p2.dem",
    ]


def test_rounds_preserve_match_numbers(multipart: Demo) -> None:
    assert multipart.rounds["round_num"].to_list() == list(range(1, 25))


def test_tables_keep_local_ticks_in_separate_parts(multipart: Demo) -> None:
    for index, part in enumerate(multipart.parts):
        actual = multipart.kills.filter(pl.col("part") == index).drop("part")
        assert_frame_equal(actual, part.kills)


def test_part_column_is_unsigned(multipart: Demo) -> None:
    assert multipart.kills.schema["part"] == pl.UInt32


@pytest.mark.parametrize("options", [{"ticks": 10}, {"start_tick": 0}, {"end_tick": 20}])
def test_local_tick_queries_require_a_part(multipart: Demo, options: dict) -> None:
    with pytest.raises(ValueError, match="select part"):
        multipart.snapshots(**options)


def test_explicit_part_queries_keep_local_ticks(multipart: Demo) -> None:
    actual = multipart.snapshots(part=1, ticks=5333).drop("part")
    assert_frame_equal(actual, multipart.parts[1].snapshots(ticks=5333))


def test_single_file_queries_keep_their_schema(multipart: Demo) -> None:
    assert "part" not in multipart.parts[1].snapshots(ticks=5333).columns


def test_statistics_use_all_completed_rounds(multipart: Demo) -> None:
    assert multipart.stats["rounds_played"].to_list() == [24] * 10


def test_statistics_exclude_freeze_restart_deaths(multipart: Demo) -> None:
    assert multipart.stats["deaths"].sum() == 172


def test_raw_events_preserve_freeze_restart_deaths(multipart: Demo) -> None:
    assert multipart.kills.filter((pl.col("part") == 1) & (pl.col("tick") == 9)).height == 10


@pytest.mark.parametrize("include_knife_rounds", [False, True])
def test_statistics_cache_each_knife_round_variant(
    multipart: Demo, include_knife_rounds: bool
) -> None:
    assert multipart.player_stats(include_knife_rounds) is multipart.player_stats(
        include_knife_rounds
    )


def test_event_counts_add_occurrences_from_each_part(multipart: Demo) -> None:
    count = sum(part.events.counts["player_death"] for part in multipart.parts)
    assert multipart.events.counts["player_death"] == count


def test_event_frame_cache_is_shared_by_lookup_styles(multipart: Demo) -> None:
    assert multipart.events.player_death is multipart.events["player_death"]


def test_header_keeps_playback_metadata_per_part(multipart: Demo) -> None:
    assert "playback_ticks" not in multipart.header
    assert all("playback_ticks" in header for header in multipart.headers)


def test_multipart_path_requires_the_paths_property(multipart: Demo) -> None:
    with pytest.raises(ValueError, match="use paths"):
        _ = multipart.path


def test_parts_keep_the_public_demo_api(multipart: Demo) -> None:
    assert all(isinstance(part, Demo) for part in multipart.parts)


def test_parts_reuse_the_native_frame_cache(multipart: Demo) -> None:
    assert multipart.parts[1].kills is multipart.parts[1].kills


def test_pistol_detection_spans_recording_boundaries(multipart: Demo) -> None:
    pistols = multipart.round_economy.filter(pl.col("buy_type") == "pistol")
    assert pistols["round_num"].unique().sort().to_list() == [1, 13]


def test_event_queries_skip_parts_without_matches(multipart: Demo) -> None:
    assert multipart.snapshots(events="bomb_exploded")["part"].unique().to_list() == [0]


def test_reversed_parts_are_rejected(multipart: Demo) -> None:
    with pytest.raises(ValueError, match="rounds"):
        Demo(list(reversed(multipart.paths)))


@pytest.fixture
def multipart_control(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    from awpy import map_control

    snaps = pl.DataFrame({"part": [0, 1], "tick": [10, 10]})
    fires = pl.DataFrame({"part": [0, 1], "start_tick": [0, 0], "end_tick": [20, 20]})
    calls = []
    monkeypatch.setattr(map_control, "_resolve_map", lambda *_: "de_overpass")
    monkeypatch.setattr(map_control, "_nav", lambda *_: None)
    monkeypatch.setattr(map_control, "_occluders", lambda *_: (pl.DataFrame(), fires))

    def compute(tick: int, group: pl.DataFrame, **options: object) -> dict:
        calls.append((group, options["fires"]))
        return {
            key: 0.0
            for key in (
                "ct_fraction",
                "t_fraction",
                "contested_fraction",
                "neutral_fraction",
                "net_control",
            )
        }

    monkeypatch.setattr(map_control, "_compute_at", compute)
    demo = SimpleNamespace(snapshots=lambda **_: snaps)
    result = map_control.map_control(demo, every=64, method="reachability")
    return SimpleNamespace(result=result, calls=calls)


def test_map_control_keeps_equal_ticks_separate(multipart_control: SimpleNamespace) -> None:
    assert multipart_control.result.select("part", "tick").rows() == [(0, 10), (1, 10)]


def test_map_control_excludes_other_parts_occluders(multipart_control: SimpleNamespace) -> None:
    assert [
        (group["part"].to_list(), fires["part"].to_list())
        for group, fires in multipart_control.calls
    ] == [([0], [0]), ([1], [1])]
