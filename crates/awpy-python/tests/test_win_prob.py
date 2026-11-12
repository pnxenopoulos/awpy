"""Tests for awpy.win_prob and its round plot (offline; the demo and models are fakes)."""

import json
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
from typing import cast

import matplotlib
import matplotlib.pyplot as plt
import polars as pl
import pytest
from awpy import Demo, data, plot, win_prob
from awpy._win_prob_features import features_at
from awpy.cli import app
from matplotlib.collections import LineCollection
from matplotlib.colors import to_hex
from typer.testing import CliRunner

matplotlib.use("Agg")

CT, T = "counter-terrorist", "terrorist"
#: Enemy kills at ticks 11, 13 (no snapshot), and 17, and a team kill at tick 18.
KILLS = ((11, 1, 2, CT, T), (13, 1, 3, CT, T), (17, 2, 1, T, CT), (18, 2, 3, T, T))


def combat(rows: Iterable[tuple]) -> pl.DataFrame:
    schema = {"tick": pl.Int32, "attacker_steamid": pl.UInt64, "victim_steamid": pl.UInt64}
    schema |= {"attacker_side": pl.String, "victim_side": pl.String}
    return pl.DataFrame(rows, schema=schema, orient="row")


class RoundDemo:
    """One round, live from tick 10 to tick 20, with a plant at tick 15.

    Each tick has one live CT, one live T, and one dead T, except tick 13.
    """

    paths = (Path("match.dem"),)
    tick_rate = 4.0
    header = {"map_name": "de_mirage"}
    rounds = pl.DataFrame({"round_num": [1], "freeze_end_tick": [10], "end_tick": [20]}).cast(
        pl.Int32
    )
    bomb = pl.DataFrame(
        {"tick": [15], "event": ["finish_plant"], "bombsite": ["A"], "x": [0], "y": [0], "z": [0]}
    ).with_columns(pl.col("tick").cast(pl.Int32))

    def __init__(self, damages: Iterable[tuple] = (), kills: Iterable[tuple] = KILLS) -> None:
        self.damages, self.kills = combat(damages), combat(kills)

    def load(self, *datasets: str) -> None:
        pass

    def snapshots(self, *, ticks: list[int]) -> pl.DataFrame:
        players = ((CT, 70, 3, 4, 0, "m4a1"), (T, 90, 0, 0, 12, "ak47"), (T, 0, 0, 0, 0, "ak47"))
        return pl.DataFrame(
            [(tick, *player) for tick in ticks if tick != 13 for player in players],
            schema={
                "tick": pl.Int32,
                "side": pl.String,
                "health": pl.Int32,
                "x": pl.Float64,
                "y": pl.Float64,
                "z": pl.Float64,
                "primary_weapon": pl.String,
            },
            orient="row",
        ).with_columns(
            armor=50,
            has_helmet=True,
            has_defuser=True,
            fire_grenades=1,
            smoke_grenades=1,
            he_grenades=1,
            equipment_value=1000,
            flashbangs=2,
            is_defusing=True,
        )


def round_demo(**events) -> Demo:
    return cast(Demo, RoundDemo(**events))


def fake_model(**reasons: float | pl.Expr) -> win_prob.RoundEndModel:
    """A model that gives each reason a constant or a function of ``tick``."""
    return win_prob.RoundEndModel(
        win_prob.DEFAULT_MODEL,
        lambda states: states.select("tick").with_columns(**reasons).drop("tick"),
    )


#: CT win probability is always 0.375.
MODEL = fake_model(bomb_defusal=0.25, ct_eliminated=0.5, t_eliminated=0.125, bomb_exploded=0.125)


def jump_model(t_eliminated: pl.Expr) -> win_prob.RoundEndModel:
    return fake_model(t_eliminated=t_eliminated, ct_eliminated=1 - t_eliminated)


#: CT win probability goes from 50% to 75% at tick 11, and back to 50% at tick 12.
WPA_MODEL = jump_model(pl.when(pl.col("tick") == 11).then(0.75).otherwise(0.5))


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def test_round_features_use_the_plant_only_after_it_completes() -> None:
    states = features_at(round_demo(), [14, 15, 16])
    assert states.select(
        "phase",
        "time_since_phase_start",
        "bombsite",
        "defuse_in_progress",
        "ct_distance_to_bomb",
        "t_distance_to_bomb",
    ).rows() == [
        ("bomb_not_planted", 1.0, None, False, None, None),
        ("bomb_planted", 0.0, "A", True, 5.0, 12.0),
        ("bomb_planted", 0.25, "A", True, 5.0, 12.0),
    ]


def test_only_live_players_contribute_to_equipment_features() -> None:
    state = features_at(round_demo(), [10])
    assert state.select("t_dead", "t_live_hp", "t_rifles", "t_equipment_value").row(0) == (
        1,
        90,
        1,
        1000,
    )


def test_predict_keeps_tick_order_and_duplicates() -> None:
    ticks = MODEL.predict(round_demo(), ticks=pl.Series([15, 10, 15]))["tick"]
    assert ticks.to_list() == [15, 10, 15]


def test_predict_sums_reasons_by_winning_side() -> None:
    assert MODEL.predict(round_demo(), ticks=15).select(
        "predicted_round_end_reason", "time_ran_out", "ct_win_probability", "t_win_probability"
    ).row(0) == ("ct_eliminated", 0.0, 0.375, 0.625)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda demo: MODEL.predict(demo, ticks=9), "outside"),
        (lambda demo: MODEL.predict(demo, ticks=13), "no CT or T"),
        (lambda demo: MODEL.predict(demo, ticks=10, part=1), "part"),
        (lambda demo: MODEL.wpa(demo, round_num=2), "round 2"),
    ],
)
def test_unavailable_ticks_parts_and_rounds_raise(call, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        call(round_demo())


@pytest.mark.parametrize("dataset", ["damages", "kills"])
@pytest.mark.parametrize("attack", [(11, 1, 2, CT, T), (12, 1, 2, T, CT)])
def test_wpa_credits_attacker_and_debits_victim(dataset: str, attack: tuple) -> None:
    demo = round_demo(**{"damages": [], "kills": [], dataset: [attack]})
    assert WPA_MODEL.wpa(demo, round_num=1).rows() == [(1, 25.0), (2, -25.0)]


def test_wpa_shares_a_tick_swing_and_counts_lethal_damage_once() -> None:
    lethal_hit, other_hit = (11, 1, 2, CT, T), (11, 3, 4, CT, T)
    demo = round_demo(damages=[lethal_hit, other_hit], kills=[lethal_hit])
    assert WPA_MODEL.wpa(demo).rows() == [(1, 12.5), (3, 12.5), (2, -12.5), (4, -12.5)]


def test_wpa_gives_a_mixed_tick_swing_to_the_side_that_gained() -> None:
    demo = round_demo(damages=[(11, 1, 2, CT, T), (11, 3, 4, T, CT)], kills=[])
    assert WPA_MODEL.wpa(demo).rows() == [(1, 25.0), (3, 0.0), (4, 0.0), (2, -25.0)]


@pytest.mark.parametrize("tick", [9, 10, 13, 14, 21])
def test_wpa_needs_both_snapshots_in_the_same_live_round(tick: int) -> None:
    result = WPA_MODEL.wpa(round_demo(damages=[(tick, 1, 2, CT, T)], kills=[]))
    assert result.is_empty()
    assert result.schema == {"steamid": pl.UInt64, "wpa": pl.Float64}


@pytest.fixture
def model_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Serve one release from a fake download. Return the requested URLs."""
    requests = []
    context = b"the release context"
    manifest = {
        "schema_version": 1,
        "tag": f"model/{win_prob.DEFAULT_MODEL}",
        "target": "round_end_reason",
        "assets": {"round-end-reason-context.parquet": sha256(context).hexdigest()},
    }

    def download(url: str, destination: Path) -> Path:
        requests.append(url)
        if url.endswith("/model-manifest.json"):
            destination.write_text(json.dumps(manifest), encoding="utf-8")
        else:
            destination.write_bytes(context)
        return destination

    monkeypatch.setattr(data, "AWPY_DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_download", download)
    return requests


def test_get_model_uses_the_verified_cached_context(model_cache: list[str]) -> None:
    path = win_prob.get_model()
    assert win_prob.get_model() == path
    assert path.read_bytes() == b"the release context"
    assert len(model_cache) == 2
    assert data.local_versions() == []


def test_cli_downloads_versioned_model(model_cache: list[str]) -> None:
    result = CliRunner().invoke(app, ["models", "get", win_prob.DEFAULT_MODEL])
    assert result.exit_code == 0, result.output
    assert Path(result.output.strip()).is_file()
    assert model_cache[0].endswith("model%2Fkumo-round-end%2Fv1.0.0/model-manifest.json")


def test_get_model_rejects_bad_checksum(
    model_cache: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    download = data._download

    def corrupt_context(url: str, destination: Path) -> Path:
        download(url, destination)
        if url.endswith(".parquet"):
            destination.write_bytes(b"corrupt")
        return destination

    monkeypatch.setattr(data, "_download", corrupt_context)
    with pytest.raises(ValueError, match="checksum mismatch"):
        win_prob.get_model()
    assert list(data.AWPY_DATA_DIR.rglob("*.parquet")) == []


def markers(ax) -> dict:
    return {
        line.get_label(): (
            to_hex(line.get_markerfacecolor()),
            line.get_fillstyle(),
            list(zip(line.get_xdata(), line.get_ydata(), strict=True)),
        )
        for line in ax.lines
        if line.get_marker() == "o"
    }


@pytest.mark.parametrize("show", [True, False])
def test_round_plot_draws_plant_lines_in_front(show: bool) -> None:
    _, ax = plot.round_win_probability(round_demo(), 1, model=MODEL, show_bomb_plants=show)
    plants = [line for line in ax.lines if line.get_label() == "Bomb Planted"]
    assert len(plants) == show
    (trace,) = (item for item in ax.collections if isinstance(item, LineCollection))
    for plant in plants:
        assert list(plant.get_xdata()) == [1.25, 1.25]
        assert (plant.get_color(), plant.get_linestyle()) == (plot.NEUTRAL_COLOR, "-")
        assert plant.get_zorder() > trace.get_zorder()


@pytest.mark.parametrize("show", [True, False])
def test_round_plot_marks_enemy_kills_in_the_victim_color(show: bool) -> None:
    _, ax = plot.round_win_probability(round_demo(), 1, model=MODEL, show_kills=show)
    expected = {
        "CT Death": (plot.CT_COLOR.lower(), "full", [(1.75, 0.375)]),
        "T Death": (plot.T_COLOR.lower(), "full", [(0.25, 0.375)]),
    }
    assert markers(ax) == (expected if show else {})


def test_round_plot_splits_the_dot_when_both_teams_lose_a_player() -> None:
    demo = round_demo(kills=[*KILLS, (11, 2, 1, T, CT)])
    _, ax = plot.round_win_probability(demo, 1, model=MODEL)
    assert markers(ax)["Both Teams"] == (plot.CT_COLOR.lower(), "left", [(0.25, 0.375)])
    (dot,) = (line for line in ax.lines if line.get_label() == "Both Teams")
    assert dot.get_markerfacecoloralt() == plot.T_COLOR


@pytest.mark.parametrize(
    ("title", "expected"), [(None, "Round 1 | match.dem"), ("Pistol", "Pistol")]
)
def test_round_plot_title(title: str | None, expected: str) -> None:
    _, ax = plot.round_win_probability(round_demo(), 1, model=MODEL, title=title)
    assert ax.get_title(loc="left") == expected


def test_round_plot_changes_team_color_at_even_odds() -> None:
    model = jump_model(pl.when(pl.col("tick") < 11).then(0.25).otherwise(0.75))
    _, ax = plot.round_win_probability(round_demo(), 1, model=model)
    (trace,) = (item for item in ax.collections if isinstance(item, LineCollection))
    crossing = [
        (segment[:, 1].tolist(), to_hex(color))
        for segment, color in zip(trace.get_segments(), trace.get_colors(), strict=True)
        if (segment[:, 0] == 0.25).all()
    ]
    assert crossing == [([0.25, 0.5], plot.T_COLOR.lower()), ([0.5, 0.75], plot.CT_COLOR.lower())]
