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


# --- nav ------------------------------------------------------------------------


class FakeNav:
    """A stand-in for :class:`awpy.NavMesh`.

    A real nav mesh means parsing a binary Source 2 ``.nav`` file, which there is
    no way to fabricate here — so this exposes just the two members ``plot.nav``
    touches: ``areas`` (for the ids) and ``area()`` (for the polygon and height).
    """

    def __init__(self, areas: dict[int, tuple[list, float]]) -> None:
        self._areas = areas

    @property
    def areas(self):  # noqa: ANN201 - mirrors the real polars-returning property
        import polars as pl

        return pl.DataFrame({"area_id": list(self._areas)})

    def area(self, area_id: int) -> dict | None:
        entry = self._areas.get(int(area_id))
        if entry is None:
            return None
        corners, z = entry
        return {"area_id": area_id, "corners": corners, "centroid": (0.0, 0.0, z)}


def _square(x: float, y: float, z: float = 0.0, size: float = 10.0) -> tuple[list, float]:
    """A square area at ``(x, y)`` sitting at altitude ``z``."""
    return (
        [(x, y, z), (x + size, y, z), (x + size, y + size, z), (x, y + size, z)],
        z,
    )


@pytest.fixture
def fake_nav(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Install a FakeNav factory in place of ``awpy.NavMesh``."""

    def install(areas: dict[int, tuple[list, float]]) -> None:
        import awpy

        monkeypatch.setattr(awpy, "NavMesh", lambda *a, **k: FakeNav(areas))

    return install


def test_nav_fills_every_area(cache: Path, fake_nav) -> None:  # noqa: ANN001
    fake_nav({1: _square(0, 0), 2: _square(20, 0), 3: _square(40, 0)})
    fig, ax = plot.nav("de_flat")
    assert len(ax.patches) == 3
    assert len(ax.images) == 1  # the radar underneath


def test_nav_highlight_uses_a_distinct_color_on_top(cache: Path, fake_nav) -> None:  # noqa: ANN001
    fake_nav({1: _square(0, 0), 2: _square(20, 0), 3: _square(40, 0)})
    fig, ax = plot.nav("de_flat", highlight=[2])
    assert len(ax.patches) == 3  # every area still drawn, just recolored

    highlighted = [p for p in ax.patches if p.get_zorder() == 6]
    assert len(highlighted) == 1
    # Highlights sit above the base fill and are more opaque than it.
    base = [p for p in ax.patches if p.get_zorder() != 6]
    assert all(p.get_alpha() > base[0].get_alpha() for p in highlighted)
    assert highlighted[0].get_facecolor() != base[0].get_facecolor()


def test_nav_highlight_ignores_unknown_areas(cache: Path, fake_nav) -> None:  # noqa: ANN001
    """An id that isn't in the mesh is skipped, not an error."""
    fake_nav({1: _square(0, 0)})
    fig, ax = plot.nav("de_flat", highlight=[999])
    assert len(ax.patches) == 1  # area 1 only, drawn as base


def test_nav_skips_degenerate_areas(cache: Path, fake_nav) -> None:  # noqa: ANN001
    """Fewer than three corners is not a polygon."""
    fake_nav({1: _square(0, 0), 2: ([(0.0, 0.0, 0.0), (1.0, 1.0, 0.0)], 0.0)})
    fig, ax = plot.nav("de_flat")
    assert len(ax.patches) == 1


def test_nav_filters_to_the_level_being_drawn(cache: Path, fake_nav) -> None:  # noqa: ANN001
    # de_duplex puts z < -100 on the lower level.
    fake_nav({1: _square(0, 0, z=0.0), 2: _square(20, 0, z=-500.0), 3: _square(40, 0, z=-600.0)})

    fig, ax = plot.nav("de_duplex")
    assert len(ax.patches) == 1  # the one upper area

    fig, ax = plot.nav("de_duplex", lower=True)
    assert len(ax.patches) == 2  # the two lower areas


def test_nav_legend_reports_counts_and_level(cache: Path, fake_nav) -> None:  # noqa: ANN001
    fake_nav({1: _square(0, 0), 2: _square(20, 0)})

    fig, ax = plot.nav("de_flat")
    assert "2 nav areas" in ax.texts[0].get_text()

    fig, ax = plot.nav("de_flat", highlight=[1])
    assert "1 highlighted" in ax.texts[0].get_text()

    fig, ax = plot.nav("de_flat", legend=False)
    assert not ax.texts

    # A multi-level map says which level the count is for, since it is per level.
    fake_nav({1: _square(0, 0, z=0.0)})
    fig, ax = plot.nav("de_duplex")
    assert "upper level" in ax.texts[0].get_text()
    fig, ax = plot.nav("de_duplex", lower=True)
    assert "lower level" in ax.texts[0].get_text()


def test_nav_accepts_an_existing_axes(cache: Path, fake_nav) -> None:  # noqa: ANN001
    fake_nav({1: _square(0, 0)})
    fig, ax = plot.radar("de_flat")
    fig2, ax2 = plot.nav("de_flat", ax=ax)
    assert ax2 is ax


def test_player_bars_track_save_dpi(cache: Path) -> None:
    """HP/armor bars must scale with the dpi a figure is *saved* at.

    ``_marker_offset`` used to bake ``fig.dpi / 72`` into a static transform. The
    marker, label, and yaw tick are sized by matplotlib's own point handling, which
    follows the dpi override ``savefig(dpi=...)`` applies — so a frozen factor left
    the bars at a fixed pixel size while everything around them scaled: oversized
    at low dpi, and shrunk *inside* the marker when saving at high dpi.
    """
    fig, ax = plot.frame("de_flat", [plot.Player(x=0.0, y=0.0, side="ct", hp=100, armor=100)])
    bar = next(p for p in ax.patches if isinstance(p, matplotlib.patches.Rectangle))

    def bar_width_px() -> float:
        """The bar's width in display pixels, at the figure's current dpi."""
        transform = bar.get_transform()
        x0, x1 = bar.get_x(), bar.get_x() + bar.get_width()
        (px0, _), (px1, _) = transform.transform([(x0, 0.0), (x1, 0.0)])
        return abs(px1 - px0)

    fig.dpi = 300
    at_300 = bar_width_px()
    fig.dpi = 600
    at_600 = bar_width_px()

    assert at_300 > 0
    # Doubling the dpi must double the bar's pixel size, as it does the marker's.
    assert at_600 == pytest.approx(2 * at_300, rel=0.01)


def test_player_bars_sit_below_the_marker(cache: Path) -> None:
    """The bars belong under the circle, not inside it, at any dpi.

    A layout invariant, not the guard for the frozen-dpi bug — that one is
    :func:`test_player_bars_track_save_dpi`. This assertion has slack in it (the
    bar's top edge sits ~3x the marker radius away), so a frozen scale only trips
    it at very high dpi. It is here to catch the geometry constants drifting into
    the marker.
    """
    fig, ax = plot.frame("de_flat", [plot.Player(x=0.0, y=0.0, side="ct", hp=100, armor=100)])
    bar = next(p for p in ax.patches if isinstance(p, matplotlib.patches.Rectangle))

    # The marker is anchored in *radar-pixel* data coordinates, not world ones, so
    # the centre has to be projected the same way `frame` projects it.
    centre_px = plot.world_to_pixel("de_flat", (0.0, 0.0))

    for dpi in (150, 300, 600):
        fig.dpi = dpi
        centre = ax.transData.transform(centre_px)
        top = bar.get_transform().transform((bar.get_x(), bar.get_y()))
        gap_px = abs(top[1] - centre[1])
        marker_radius_px = plot._MARKER_RADIUS_PT * dpi / 72.0
        assert gap_px >= marker_radius_px, (
            f"at {dpi} dpi the bar's top edge is {gap_px:.1f}px from the marker "
            f"centre, inside its {marker_radius_px:.1f}px radius"
        )


# --- map_control -----------------------------------------------------------------


class FakeDemo:
    """The slice of :class:`awpy.Demo` that :func:`plot.map_control` touches."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.header = {"map_name": "de_flat"}

    def snapshots(self, *, ticks: int) -> "pl.DataFrame":  # noqa: F821, ARG002
        import polars as pl

        return pl.DataFrame(self._rows)

    @property
    def smokes(self):  # noqa: ANN201
        import polars as pl

        return pl.DataFrame(
            schema={
                "start_tick": pl.Int32,
                "end_tick": pl.Int32,
                "x": pl.Float32,
                "y": pl.Float32,
                "z": pl.Float32,
            }
        )

    fires = smokes


def _snapshot_row(**over) -> dict:  # noqa: ANN003
    row = {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "side": "ct",
        "health": 100,
        "armor": 50,
        "yaw": 90.0,
        "has_bomb": False,
    }
    row.update(over)
    return row


@pytest.fixture
def fake_map_control(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Stub out the compute layer and the nav mesh so only the drawing is exercised."""
    import awpy
    import awpy.plot as plot_mod
    import polars as pl

    control = pl.DataFrame(
        {
            "area_id": [1],
            "control": ["ct"],
            "ct": [True],
            "t": [False],
            "centroid_x": [0.0],
            "centroid_y": [0.0],
            "centroid_z": [0.0],
            "size": [100.0],
        }
    )
    monkeypatch.setattr(plot_mod, "map_control_at", lambda *a, **k: control)
    monkeypatch.setattr(awpy, "NavMesh", lambda *a, **k: FakeNav({1: _square(0, 0)}))


def test_map_control_draws_players_with_hp_and_armor(
    cache: Path, fake_map_control, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001
    """Players on a map-control plot carry the same detail as on a `frame`.

    `map_control` used to build a partial `Player` — hp but no armor — so the armor
    bar was silently dropped even though the snapshot has the value.
    """
    import awpy.plot as plot_mod

    drawn: list[plot.Player] = []
    real_draw = plot_mod._draw_player
    monkeypatch.setattr(
        plot_mod,
        "_draw_player",
        lambda ax, px, py, player, alpha: (
            drawn.append(player),
            real_draw(ax, px, py, player, alpha),
        )[1],
    )

    demo = FakeDemo([_snapshot_row(), _snapshot_row(side="t", health=40, armor=0)])
    plot.map_control(demo, tick=1000, method="vision", legend=False)

    assert len(drawn) == 2
    assert [p.hp for p in drawn] == [100, 40]
    # The whole point: armor comes through instead of defaulting to None.
    assert [p.armor for p in drawn] == [50, 0]
    assert all(p.yaw is not None for p in drawn)


def test_map_control_player_gets_both_bars(cache: Path, fake_map_control) -> None:  # noqa: ANN001
    """Each drawn player yields both an HP and an armor bar (3 patches each)."""
    demo = FakeDemo([_snapshot_row()])
    fig, ax = plot.map_control(demo, tick=1000, method="vision", legend=False)

    bars = [p for p in ax.patches if isinstance(p, matplotlib.patches.Rectangle)]
    # Two bars, each a depleted track + filled portion + frame.
    assert len(bars) == 6
    # They sit at two distinct heights — one row per bar.
    assert len({round(b.get_y(), 3) for b in bars}) == 2


def _yaw_tick_offset(ax) -> tuple[float, float]:  # noqa: ANN001
    """The view tick's offset from the marker, in points (+x right, +y up).

    ``textcoords="offset points"`` puts the offset in **display** space, so this is
    directly comparable to how it appears on screen.
    """
    tick = next(t for t in ax.texts if getattr(t, "arrow_patch", None) is not None)
    assert tick.anncoords == "offset points"
    return tick.xyann


def test_yaw_tick_points_where_the_player_looks(cache: Path) -> None:
    """The view tick must match the world facing direction on screen.

    The offset is in display space (+y up), not radar-pixel space (+y down). Using
    the pixel convention mirrors the tick vertically: yaw 90 — world +y, which is
    *up* on the radar — drew downward, so every marker pointed at the reflection of
    where its player was actually looking.
    """
    # (yaw, expected screen direction). World +y is up on the radar, because
    # world_to_pixel flips y and the radar image inverts the axis.
    for yaw, (want_x, want_y) in {
        0.0: (1, 0),
        90.0: (0, 1),
        180.0: (-1, 0),
        270.0: (0, -1),
    }.items():
        fig, ax = plot.frame("de_flat", [plot.Player(x=0.0, y=0.0, side="ct", yaw=yaw)])
        dx, dy = _yaw_tick_offset(ax)
        # Component along the expected axis must be positive, and there must be no
        # drift along the perpendicular one.
        along = dx * want_x + dy * want_y
        across = dx * want_y + dy * want_x
        assert along > 0, f"yaw={yaw}: tick points backwards (dx={dx:.2f}, dy={dy:.2f})"
        assert abs(across) < 1e-9, f"yaw={yaw}: tick drifts off axis (dx={dx:.2f}, dy={dy:.2f})"


def test_yaw_tick_is_not_mirrored_diagonally(cache: Path) -> None:
    """A diagonal catches a mirror the cardinal directions could let through."""
    fig, ax = plot.frame("de_flat", [plot.Player(x=0.0, y=0.0, side="ct", yaw=45.0)])
    dx, dy = _yaw_tick_offset(ax)
    # yaw 45 is up and to the right, in equal measure.
    assert dx > 0 and dy > 0, f"expected up-right, got dx={dx:.2f} dy={dy:.2f}"
    assert dx == pytest.approx(dy, rel=1e-6)


def test_yaw_tick_length_is_the_marker_radius(cache: Path) -> None:
    """The tick reaches the marker edge — no further, so it stays inside the circle."""
    fig, ax = plot.frame("de_flat", [plot.Player(x=0.0, y=0.0, side="ct", yaw=30.0)])
    dx, dy = _yaw_tick_offset(ax)
    assert (dx**2 + dy**2) ** 0.5 == pytest.approx(plot._MARKER_RADIUS_PT, rel=1e-6)
