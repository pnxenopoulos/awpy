"""Multipart input, query scope, and cache behavior without replay decoding."""

from pathlib import Path
from types import SimpleNamespace
from weakref import ref

import polars as pl
import pytest
from awpy import Demo
from awpy import demo as demo_module


class RawEvents:
    def __init__(self, frames: dict[str, pl.DataFrame]) -> None:
        self.frames = frames
        self.counts = {name: frame.height for name, frame in frames.items()}

    def __contains__(self, name: str) -> bool:
        return name in self.frames

    def __getitem__(self, name: str) -> pl.DataFrame:
        return self.frames[name]


@pytest.fixture
def native_parts(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    settings: list[dict] = [{}, {}]
    created = []
    stat_calls = []
    names = Demo.available_datasets()

    class Native:
        def __init__(self, path: Path) -> None:
            self.index = len(created)
            config = settings[self.index]
            self.path = path
            self.header = {
                "map_name": "de_overpass",
                "build_num": 1,
                "playback_ticks": 100,
                "playback_frames": 100,
                "playback_time": 1.0,
                **config.get("header", {}),
            }
            self.tick_rate = config.get("tick_rate", 64.0)
            self.coverage = config.get("coverage", (True, True))
            self.rounds = pl.DataFrame(
                {
                    "round_num": config.get("rounds", [self.index + 1]),
                }
            ).with_columns(
                pl.lit(False).alias("is_knife_round"),
                pl.lit(config.get("freeze_end_tick", 10)).alias("freeze_end_tick"),
            )
            self.players = pl.DataFrame(
                {
                    "steamid": pl.Series([1, 0], dtype=pl.UInt64),
                    "name": [f"player-{self.index}", f"observer-{self.index}"],
                    "side": ["terrorist", None],
                    "team_clan_name": ["team", None],
                }
            )
            self.kills = pl.DataFrame({"tick": [10], "weapon": ["ak47"]})
            self.events = RawEvents(
                {
                    "player_death": pl.DataFrame({"tick": [10], f"field_{self.index}": ["value"]}),
                    **config.get("events", {}),
                }
            )
            self.convars = {"mode": str(self.index)}
            self.stats = pl.DataFrame({"steamid": [1], "kills": [self.index + 1]})
            self.load_calls = []
            self.snapshot_calls = []
            created.append(self)

        @staticmethod
        def available_datasets() -> list[str]:
            return names

        def _round_coverage(self) -> tuple[bool, bool]:
            return self.coverage

        def load(self, *datasets: str) -> None:
            self.load_calls.append(datasets)

        def snapshots(self, **options: object) -> pl.DataFrame:
            self.snapshot_calls.append(options)
            if options.get("events") and settings[self.index].get("no_event_snapshots"):
                return pl.DataFrame(
                    schema={"tick": pl.Int64, "steamid": pl.UInt64, "side": pl.String}
                )
            return pl.DataFrame(
                {
                    "tick": [options.get("ticks") if isinstance(options.get("ticks"), int) else 10],
                    "steamid": pl.Series([1], dtype=pl.UInt64),
                    "side": ["terrorist" if self.index == 0 else "counter-terrorist"],
                }
            )

        def ticks(self, props: list[str] | None, players_only: bool) -> pl.DataFrame:
            return self.kills

        def player_stats(self, include_knife_rounds: bool) -> pl.DataFrame:
            return self.stats

        def _round_economy(self, pistols: list[int]) -> pl.DataFrame:
            return self.rounds.with_columns(pl.col("round_num").is_in(pistols).alias("is_pistol"))

        def tick_to_seconds(self, tick: int) -> float:
            return tick / self.tick_rate

        def seconds_to_tick(self, seconds: float) -> int:
            return round(seconds * self.tick_rate)

    def aggregate(parts: list, include_knife_rounds: bool) -> pl.DataFrame:
        stat_calls.append((parts, include_knife_rounds))
        return pl.DataFrame({"steamid": pl.Series([1], dtype=pl.UInt64), "kills": [3]})

    monkeypatch.setattr(demo_module, "NativeDemo", Native)
    monkeypatch.setattr(demo_module, "multipart_player_stats", aggregate)
    return SimpleNamespace(settings=settings, created=created, stat_calls=stat_calls)


@pytest.mark.parametrize(
    "source", ["first.dem", Path("first.dem"), ["first.dem"], (Path("first.dem"),)]
)
def test_paths_are_coerced_to_path_objects(native_parts: SimpleNamespace, source: object) -> None:
    parsed = Demo(source)
    assert parsed.paths == (Path("first.dem"),)
    assert native_parts.created[0].path == Path("first.dem")


def test_mixed_path_sequences_keep_the_supplied_order(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", Path("second.dem")])
    assert parsed.paths == (Path("first.dem"), Path("second.dem"))


@pytest.mark.parametrize("source", [[], ()])
def test_empty_sequences_are_rejected(source: object) -> None:
    with pytest.raises(ValueError, match="at least one"):
        Demo(source)


@pytest.mark.parametrize("source", [1, b"file.dem", {"file.dem"}, iter(["file.dem"])])
def test_non_path_inputs_are_rejected(source: object) -> None:
    with pytest.raises(TypeError):
        Demo(source)


def test_repeated_paths_are_rejected_before_opening_files(native_parts: SimpleNamespace) -> None:
    with pytest.raises(ValueError, match="must not repeat"):
        Demo(["first.dem", "./first.dem"])
    assert not native_parts.created


@pytest.mark.parametrize("key,value", [("map_name", "de_mirage"), ("build_num", 2)])
def test_incompatible_headers_are_rejected(
    native_parts: SimpleNamespace, key: str, value: object
) -> None:
    native_parts.settings[1]["header"] = {key: value}
    with pytest.raises(ValueError, match=f"different {key}"):
        Demo(["first.dem", "second.dem"])


def test_incompatible_tick_rates_are_rejected(native_parts: SimpleNamespace) -> None:
    native_parts.settings[1]["tick_rate"] = 128.0
    with pytest.raises(ValueError, match="tick rate"):
        Demo(["first.dem", "second.dem"])


@pytest.mark.parametrize("coverage", [(False, True), (True, False), (None, None)])
def test_incomplete_round_boundaries_are_rejected(
    native_parts: SimpleNamespace, coverage: tuple
) -> None:
    native_parts.settings[1]["coverage"] = coverage
    with pytest.raises(ValueError, match="boundaries"):
        Demo(["first.dem", "second.dem"])


@pytest.mark.parametrize("rounds", [[1], [3], [2, 4], [2, 2]])
def test_overlapping_or_missing_rounds_are_rejected(
    native_parts: SimpleNamespace, rounds: list[int]
) -> None:
    native_parts.settings[1]["rounds"] = rounds
    with pytest.raises(ValueError, match="rounds"):
        Demo(["first.dem", "second.dem"])


def test_rounds_preserve_match_numbers(native_parts: SimpleNamespace) -> None:
    native_parts.settings[0]["rounds"] = [1, 2]
    native_parts.settings[1]["rounds"] = [3, 4]
    assert Demo(["first.dem", "second.dem"]).rounds["round_num"].to_list() == [1, 2, 3, 4]


def test_tables_keep_equal_ticks_in_separate_parts(native_parts: SimpleNamespace) -> None:
    frame = Demo(["first.dem", "second.dem"]).kills
    assert frame.select("part", "tick").rows() == [(0, 10), (1, 10)]
    assert frame.schema["part"] == pl.UInt32


@pytest.mark.parametrize("options", [{"ticks": 10}, {"start_tick": 0}, {"end_tick": 20}])
def test_local_tick_queries_require_a_part(native_parts: SimpleNamespace, options: dict) -> None:
    with pytest.raises(ValueError, match="select part"):
        Demo(["first.dem", "second.dem"]).snapshots(**options)


def test_explicit_part_queries_only_decode_that_part(native_parts: SimpleNamespace) -> None:
    frame = Demo(["first.dem", "second.dem"]).snapshots(part=1, ticks=9)
    assert frame.select("part", "tick").rows() == [(1, 9)]
    assert not native_parts.created[0].snapshot_calls


def test_stride_queries_read_each_part(native_parts: SimpleNamespace) -> None:
    frame = Demo(["first.dem", "second.dem"]).snapshots(every=64)
    assert frame["part"].to_list() == [0, 1]


@pytest.mark.parametrize("part", [-1, 2])
def test_invalid_part_indices_are_rejected(native_parts: SimpleNamespace, part: int) -> None:
    with pytest.raises(ValueError, match="part must"):
        Demo(["first.dem", "second.dem"]).snapshots(part=part, ticks=10)


def test_tick_tables_include_the_selected_part(native_parts: SimpleNamespace) -> None:
    assert Demo(["first.dem", "second.dem"]).ticks(part=1)["part"].to_list() == [1]


def test_single_file_datasets_keep_native_frames(native_parts: SimpleNamespace) -> None:
    parsed = Demo("first.dem")
    assert parsed.kills is native_parts.created[0].kills


def test_single_file_snapshots_keep_their_schema(native_parts: SimpleNamespace) -> None:
    assert "part" not in Demo("first.dem").snapshots(ticks=10).columns


def test_players_combine_by_steam_id(native_parts: SimpleNamespace) -> None:
    players = Demo(["first.dem", "second.dem"]).players
    assert players.filter(pl.col("steamid") == 1)["name"].to_list() == ["player-1"]


def test_observers_with_zero_steam_ids_stay_distinct(native_parts: SimpleNamespace) -> None:
    players = Demo(["first.dem", "second.dem"]).players
    assert players.filter(pl.col("steamid") == 0)["name"].to_list() == ["observer-0", "observer-1"]


def test_statistics_use_native_exact_totals(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", "second.dem"])
    assert parsed.stats["kills"].to_list() == [3]
    assert native_parts.stat_calls == [(native_parts.created, False)]


def test_statistics_cache_each_knife_round_variant(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", "second.dem"])
    assert parsed.stats is parsed.player_stats()
    assert parsed.player_stats(True) is parsed.player_stats(True)
    assert [call[1] for call in native_parts.stat_calls] == [False, True]


def test_event_frames_keep_the_union_of_fields(native_parts: SimpleNamespace) -> None:
    frame = Demo(["first.dem", "second.dem"]).events.player_death
    assert set(frame.columns) == {"tick", "part", "field_0", "field_1"}
    assert frame.height == 2


def test_event_counts_add_occurrences_from_each_part(native_parts: SimpleNamespace) -> None:
    assert Demo(["first.dem", "second.dem"]).events.counts == {"player_death": 2}


def test_missing_events_raise_key_error(native_parts: SimpleNamespace) -> None:
    with pytest.raises(KeyError):
        Demo(["first.dem", "second.dem"]).events["missing"]


def test_missing_event_attributes_raise_attribute_error(native_parts: SimpleNamespace) -> None:
    with pytest.raises(AttributeError):
        _ = Demo(["first.dem", "second.dem"]).events.missing


def test_event_frame_cache_is_shared_by_lookup_styles(native_parts: SimpleNamespace) -> None:
    events = Demo(["first.dem", "second.dem"]).events
    assert events.player_death is events["player_death"]


def test_header_keeps_playback_metadata_per_part(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", "second.dem"])
    assert "playback_ticks" not in parsed.header
    assert [header["playback_ticks"] for header in parsed.headers] == [100, 100]


def test_convars_use_the_latest_recorded_value(native_parts: SimpleNamespace) -> None:
    assert Demo(["first.dem", "second.dem"]).convars == {"mode": "1"}


def test_multipart_path_requires_the_paths_property(native_parts: SimpleNamespace) -> None:
    with pytest.raises(ValueError, match="use paths"):
        _ = Demo(["first.dem", "second.dem"]).path


def test_unknown_load_datasets_fail_before_decoding(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", "second.dem"])
    with pytest.raises(ValueError, match="unknown dataset"):
        parsed.load("kills", "missing")
    assert not any(part.load_calls for part in native_parts.created)


def test_load_batches_within_each_recording(native_parts: SimpleNamespace) -> None:
    Demo(["first.dem", "second.dem"]).load("rounds", "kills")
    assert [part.load_calls for part in native_parts.created] == [[("rounds", "kills")]] * 2


def test_pistol_detection_spans_recording_boundaries(native_parts: SimpleNamespace) -> None:
    frame = Demo(["first.dem", "second.dem"]).round_economy
    assert frame.filter(pl.col("is_pistol"))["round_num"].to_list() == [1, 2]


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


def test_parts_keep_the_public_demo_api(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", "second.dem"])
    assert all(isinstance(part, Demo) for part in parsed.parts)


def test_parts_reuse_existing_native_parsers(native_parts: SimpleNamespace) -> None:
    parsed = Demo(["first.dem", "second.dem"])
    assert parsed.parts[1].kills is native_parts.created[1].kills
    assert len(native_parts.created) == 2


def test_single_file_is_its_own_only_part(native_parts: SimpleNamespace) -> None:
    parsed = Demo("first.dem")
    assert parsed.parts == (parsed,)


def test_event_queries_skip_parts_without_matches(native_parts: SimpleNamespace) -> None:
    native_parts.settings[0]["no_event_snapshots"] = True
    frame = Demo(["first.dem", "second.dem"]).snapshots(events="player_death")
    assert frame["part"].to_list() == [1]


def test_missing_round_start_evidence_is_rejected(native_parts: SimpleNamespace) -> None:
    native_parts.settings[1]["freeze_end_tick"] = None
    with pytest.raises(ValueError, match="round-start evidence"):
        Demo(["first.dem", "second.dem"])


def test_reading_single_file_parts_does_not_retain_the_demo(native_parts: SimpleNamespace) -> None:
    parsed = Demo("first.dem")
    assert parsed.parts[0] is parsed
    reference = ref(parsed)
    del parsed
    assert reference() is None
