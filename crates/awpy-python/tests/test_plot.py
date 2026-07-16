"""Tests for awpy.plot (offline; radar images and map data are fabricated)."""

import json
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from awpy import data, plot

matplotlib.use("Agg")

# A flat map and a two-level map, on a fabricated release "9".
MAP_DATA = {
    "de_flat": {"pos_x": -512.0, "pos_y": 512.0, "scale": 1.0},
    "de_duplex": {
        "pos_x": -2048.0,
        "pos_y": 2048.0,
        "scale": 4.0,
        "verticalsections": {
            "default": {"AltitudeMin": "-100", "AltitudeMax": "10000"},
            "lower": {"AltitudeMin": "-10000", "AltitudeMax": "-100"},
        },
    },
}


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fabricate a cached release with map_data.json and radar PNGs."""
    monkeypatch.setattr(data, "AWPY_DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_latest_cache", None)
    release = tmp_path / "9"
    radars = release / "radars"
    radars.mkdir(parents=True)
    (release / "map_data.json").write_text(json.dumps(MAP_DATA))
    (release / ".images.zip.done").touch()
    image = np.zeros((16, 16, 3))
    for name in ("de_flat", "de_duplex", "de_duplex_lower"):
        plt.imsave(radars / f"{name}.png", image)
    return tmp_path


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


# --- coordinates ---------------------------------------------------------------


def test_world_to_pixel_known_values(cache: Path) -> None:
    assert plot.world_to_pixel("de_flat", (0.0, 0.0)) == (512.0, 512.0)
    assert plot.world_to_pixel("de_flat", (-512.0, 512.0)) == (0.0, 0.0)
    # Scale divides, and pixel y grows as world y falls.
    assert plot.world_to_pixel("de_duplex", (0.0, -2048.0)) == (512.0, 1024.0)


def test_pixel_world_round_trip(cache: Path) -> None:
    world = (123.5, -456.25)
    assert plot.pixel_to_world("de_duplex", plot.world_to_pixel("de_duplex", world)) == world


def test_transform_pins_version(cache: Path) -> None:
    other = dict(MAP_DATA, de_flat={"pos_x": 0.0, "pos_y": 0.0, "scale": 1.0})
    release = cache / "10"
    release.mkdir()
    (release / "map_data.json").write_text(json.dumps(other))

    assert plot.world_to_pixel("de_flat", (0.0, 0.0), version=9) == (512.0, 512.0)
    assert plot.world_to_pixel("de_flat", (0.0, 0.0), version=10) == (0.0, 0.0)
    # Unpinned resolves to the newest cached release (10).
    assert plot.world_to_pixel("de_flat", (0.0, 0.0)) == (0.0, 0.0)


def test_unknown_map_raises(cache: Path) -> None:
    with pytest.raises(KeyError, match="de_nonexistent"):
        plot.world_to_pixel("de_nonexistent", (0.0, 0.0))


def test_is_lower_level(cache: Path) -> None:
    assert plot.is_lower_level("de_duplex", -500.0)
    assert not plot.is_lower_level("de_duplex", 50.0)
    assert not plot.is_lower_level("de_flat", -500.0)  # single-level map


def test_has_lower_level(cache: Path) -> None:
    assert plot.has_lower_level("de_duplex")
    assert not plot.has_lower_level("de_flat")


# --- radar / frame ---------------------------------------------------------------


def test_radar_draws_image(cache: Path) -> None:
    fig, ax = plot.radar("de_flat")
    assert len(ax.images) == 1
    assert not ax.axison


def test_radar_lower_level(cache: Path) -> None:
    fig, ax = plot.radar("de_duplex", lower=True)
    assert len(ax.images) == 1


def test_radar_missing_map_raises(cache: Path) -> None:
    with pytest.raises(FileNotFoundError):
        plot.radar("de_nonexistent")


def test_frame_draws_players_and_bomb(cache: Path) -> None:
    players = [
        plot.Player(x=0.0, y=0.0, side="t", hp=80, armor=50, yaw=90.0, label="a"),
        plot.Player(x=10.0, y=10.0, side="ct"),
        plot.Player(x=20.0, y=20.0, hp=0),  # dead -> cross marker
        plot.Player(x=99999.0, y=0.0),  # off the radar -> dropped
    ]
    fig, ax = plot.frame("de_flat", players, bomb=(5.0, 5.0, 0.0))
    # 2 alive markers + 1 dead cross + 1 bomb = 4 scatter collections.
    assert len(ax.collections) == 4
    assert len(ax.patches) == 6  # hp + armor bars (depleted track + fill + border each)
    # The yaw tick is an (empty-text) annotation; only the label carries text.
    assert [t.get_text() for t in ax.texts if t.get_text()] == ["a"]


def test_frame_bomb_carrier_border(cache: Path) -> None:
    import matplotlib.colors as mcolors

    players = [
        plot.Player(x=0.0, y=0.0, side="t", has_bomb=True),  # red border
        plot.Player(x=10.0, y=10.0, side="t"),  # black border
    ]
    fig, ax = plot.frame("de_flat", players)
    # No extra artist: the carrier's own marker edge turns red.
    assert len(ax.collections) == 2
    edges = [tuple(c.get_edgecolor()[0]) for c in ax.collections]
    assert mcolors.to_rgba(plot._BOMB_CARRIER_BORDER) in edges
    assert mcolors.to_rgba("black") in edges


def test_frame_planted_bomb_border(cache: Path) -> None:
    import matplotlib.colors as mcolors

    fig, ax = plot.frame("de_flat", [], bomb=(0.0, 0.0, 0.0), bomb_planted=True)
    assert len(ax.collections) == 1  # just the diamond, with a green edge
    assert tuple(ax.collections[0].get_edgecolor()[0]) == mcolors.to_rgba(plot._BOMB_PLANTED_BORDER)
    # Unplanted: the diamond keeps its black edge.
    fig, ax = plot.frame("de_flat", [], bomb=(0.0, 0.0, 0.0))
    assert tuple(ax.collections[0].get_edgecolor()[0]) == mcolors.to_rgba("black")


def test_frame_draws_smokes_fires_and_grenades(cache: Path) -> None:
    from matplotlib.patches import Circle

    fig, ax = plot.frame(
        "de_flat",
        [],
        smokes=[(0.0, 0.0, 0.0), (100.0, 100.0)],  # z optional
        fires=[(50.0, 50.0, 0.0)],
        grenades=[
            (0.0, 0.0),  # bare position, default color
            {"pos": (30.0, 30.0), "type": "he"},  # dict with a type
        ],
    )
    # 2 smoke discs + 1 fire disc = 3 Circle patches; grenades are markers.
    assert sum(isinstance(p, Circle) for p in ax.patches) == 3
    assert len(ax.collections) == 2  # 2 grenade markers
    assert not ax.lines


def test_frame_grenade_color_by_type(cache: Path) -> None:
    import matplotlib.colors as mcolors

    fig, ax = plot.frame(
        "de_flat",
        [],
        grenades=[
            {"pos": (0.0, 0.0), "type": "molotov"},  # type -> palette
            {"x": 1.0, "y": 1.0, "color": "magenta"},  # row-shaped, explicit color
        ],
    )
    got = [tuple(coll.get_facecolor()[0]) for coll in ax.collections]
    assert got[0] == mcolors.to_rgba(plot._FIRE_COLOR)
    assert got[1] == mcolors.to_rgba("magenta")


def test_frame_area_effects_respect_level(cache: Path) -> None:
    # On a multi-level map, a lower-level smoke is hidden when drawing the upper.
    fig, ax = plot.frame("de_duplex", [], smokes=[(0.0, 0.0, -500.0)], off_level_alpha=0.0)
    from matplotlib.patches import Circle

    assert sum(isinstance(p, Circle) for p in ax.patches) == 0
    fig, ax = plot.frame("de_duplex", [], smokes=[(0.0, 0.0, -500.0)], lower=True)
    assert sum(isinstance(p, Circle) for p in ax.patches) == 1


def test_frame_hides_off_level_players_when_asked(cache: Path) -> None:
    players = [plot.Player(x=0.0, y=0.0, z=-500.0), plot.Player(x=0.0, y=0.0, z=50.0)]
    fig, ax = plot.frame("de_duplex", players, off_level_alpha=0.0)
    assert len(ax.collections) == 1  # only the upper-level player
    fig, ax = plot.frame("de_duplex", players, lower=True, off_level_alpha=0.0)
    assert len(ax.collections) == 1  # only the lower-level player


def test_frame_side_colors() -> None:
    assert plot.Player(x=0, y=0, side="T")._color == plot.T_COLOR
    assert plot.Player(x=0, y=0, side="ct")._color == plot.CT_COLOR
    # The demo dataframes spell sides out in full.
    assert plot.Player(x=0, y=0, side="terrorist")._color == plot.T_COLOR
    assert plot.Player(x=0, y=0, side="counter-terrorist")._color == plot.CT_COLOR
    assert plot.Player(x=0, y=0)._color == plot.NEUTRAL_COLOR
    assert plot.Player(x=0, y=0, side="t", color="pink")._color == "pink"


def test_frame_levels_splits_players_by_altitude(cache: Path) -> None:
    players = [
        plot.Player(x=0.0, y=0.0, z=50.0),  # upper
        plot.Player(x=10.0, y=10.0, z=-500.0),  # lower
        plot.Player(x=20.0, y=20.0, z=-600.0),  # lower
    ]
    fig, axes = plot.frame_levels("de_duplex", players, bomb=(5.0, 5.0, -500.0))
    assert len(axes) == 2
    upper, lower = axes
    assert len(upper.images) == 1 and len(lower.images) == 1
    assert len(upper.collections) == 1  # the one upper player
    assert len(lower.collections) == 3  # two lower players + the bomb
    assert [t.get_text() for t in upper.texts] == ["upper"]
    assert [t.get_text() for t in lower.texts] == ["lower"]


def test_frame_levels_single_level_map(cache: Path) -> None:
    fig, axes = plot.frame_levels("de_flat", [plot.Player(x=0.0, y=0.0)])
    assert len(axes) == 1
    assert len(axes[0].collections) == 1
    assert not axes[0].texts  # no level labels on a single-level map


def test_frame_levels_accepts_generator(cache: Path) -> None:
    players = (plot.Player(x=float(i), y=0.0, z=z) for i, z in enumerate((50.0, -500.0)))
    fig, axes = plot.frame_levels("de_duplex", players)
    # The generator must be drained once and drawn on both panels.
    assert len(axes[0].collections) == 1
    assert len(axes[1].collections) == 1


# --- heatmap ---------------------------------------------------------------------


@pytest.mark.parametrize("method", ["hex", "hist", "kde"])
def test_heatmap_methods_draw_overlay(cache: Path, method: str) -> None:
    rng = np.random.default_rng(7)
    points = [(x, y, 0.0) for x, y in rng.normal(0.0, 100.0, size=(200, 2))]
    fig, ax = plot.heatmap("de_flat", points, method=method)
    assert len(ax.collections) == 1  # the density overlay


def test_heatmap_rejects_unknown_method(cache: Path) -> None:
    with pytest.raises(ValueError, match="method"):
        plot.heatmap("de_flat", [(0.0, 0.0)], method="voronoi")


def test_heatmap_warns_and_skips_off_level_points(cache: Path) -> None:
    points = [(0.0, 0.0, 50.0), (0.0, 0.0, -500.0)]
    with pytest.warns(UserWarning, match="lower"):
        fig, ax = plot.heatmap("de_duplex", points)
    assert len(ax.collections) == 1


def test_heatmap_empty_after_filtering(cache: Path) -> None:
    with pytest.warns(UserWarning):
        fig, ax = plot.heatmap("de_duplex", [(0.0, 0.0, -500.0)])  # all points lower
    assert len(ax.collections) == 0


def test_heatmap_accepts_xy_points(cache: Path) -> None:
    fig, ax = plot.heatmap("de_flat", [(0.0, 0.0), (10.0, 10.0)], method="hist")
    assert len(ax.collections) == 1


def test_heatmap_levels_covers_both_levels_without_warning(cache: Path) -> None:
    points = [(0.0, 0.0, 50.0), (5.0, 5.0, 60.0), (10.0, 10.0, -500.0)]
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any off-level warning would fail the test
        fig, axes = plot.heatmap_levels("de_duplex", points, method="hist")
    assert len(axes) == 2
    assert len(axes[0].collections) == 1  # upper overlay (2 points)
    assert len(axes[1].collections) == 1  # lower overlay (1 point)


def test_heatmap_levels_single_level_map(cache: Path) -> None:
    fig, axes = plot.heatmap_levels("de_flat", [(0.0, 0.0), (10.0, 10.0)])
    assert len(axes) == 1
    assert len(axes[0].collections) == 1


# --- gif -------------------------------------------------------------------------


def test_gif_writes_file(cache: Path, tmp_path: Path) -> None:
    frames = [
        [plot.Player(x=0.0, y=0.0, side="t")],
        {"players": [plot.Player(x=10.0, y=10.0, side="t")], "bomb": (0.0, 0.0, 0.0)},
    ]
    out = tmp_path / "round.gif"
    plot.gif("de_flat", frames, str(out), fps=2)
    assert out.exists()
    assert out.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
