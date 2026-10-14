"""Tests for the NavMesh navigation-mesh class."""

from pathlib import Path

import pytest
from awpy import NavMesh, data
from spatial_fixtures import square as _square
from spatial_fixtures import write_nav as _write_nav


@pytest.fixture
def chain_nav(tmp_path: Path) -> Path:
    """A 1 -> 2 -> 3 chain of adjacent unit squares."""
    nav = tmp_path / "chain.nav"
    _write_nav(
        nav,
        [
            (1, _square(0, 0, 0), [2]),
            (2, _square(1, 0, 0), [1, 3]),
            (3, _square(2, 0, 0), [2]),
        ],
    )
    return nav


@pytest.fixture
def chain_mesh(chain_nav: Path) -> NavMesh:
    return NavMesh(chain_nav)


@pytest.mark.parametrize(
    ("attribute", "expected"),
    [("area_count", 3), ("version", 35), ("sub_version", 1), ("is_analyzed", True)],
)
def test_nav_header_values(chain_mesh: NavMesh, attribute, expected) -> None:
    assert getattr(chain_mesh, attribute) == expected


def test_nav_remembers_its_source_path(chain_mesh: NavMesh, chain_nav: Path) -> None:
    assert chain_mesh.path == chain_nav


def test_nav_length_is_its_area_count(chain_mesh: NavMesh) -> None:
    assert len(chain_mesh) == 3


def test_nav_repr_shows_the_area_count(chain_mesh: NavMesh) -> None:
    assert "areas=3" in repr(chain_mesh)


def test_area_table_schema(chain_mesh: NavMesh) -> None:
    assert chain_mesh.areas.shape == (3, 9)
    assert chain_mesh.areas.columns == [
        "area_id",
        "hull_index",
        "dynamic_attribute_flags",
        "n_corners",
        "centroid_x",
        "centroid_y",
        "centroid_z",
        "size",
        "n_connections",
    ]


@pytest.mark.parametrize(
    ("column", "expected"),
    [("area_id", [1, 2, 3]), ("n_corners", [4, 4, 4]), ("n_connections", [1, 2, 1])],
)
def test_area_table_values(chain_mesh: NavMesh, column, expected) -> None:
    assert chain_mesh.areas[column].to_list() == expected


def test_area_table_sizes_use_square_units(chain_mesh: NavMesh) -> None:
    assert chain_mesh.areas["size"].to_list() == pytest.approx([1.0, 1.0, 1.0])


@pytest.fixture
def middle_area(chain_mesh: NavMesh):
    area = chain_mesh.area(2)
    assert area is not None
    return area


@pytest.mark.parametrize(
    ("field", "expected"),
    [("area_id", 2), ("connections", [1, 3]), ("ladders_above", [])],
)
def test_area_detail_values(middle_area, field, expected) -> None:
    assert middle_area[field] == expected


def test_area_detail_has_all_corners(middle_area) -> None:
    assert len(middle_area["corners"]) == 4


def test_area_detail_centroid(middle_area) -> None:
    assert middle_area["centroid"] == pytest.approx((1.5, 0.5, 0.0))


def test_area_detail_size(middle_area) -> None:
    assert middle_area["size"] == pytest.approx(1.0)


def test_unknown_area_has_no_detail(chain_mesh: NavMesh) -> None:
    assert chain_mesh.area(999) is None


@pytest.mark.parametrize(
    ("position", "expected"),
    [((0.5, 0.5, 0.0), 1), ((1.5, 0.5, 0.0), 2), ((2.5, 0.5, 0.0), 3), ((100.0, 100.0, 0.0), None)],
    ids=["first", "middle", "last", "outside"],
)
def test_find_area(chain_mesh: NavMesh, position, expected) -> None:
    assert chain_mesh.find_area(position) == expected


def test_find_area_disambiguates_by_height(tmp_path: Path) -> None:
    nav_path = tmp_path / "stacked.nav"
    _write_nav(
        nav_path,
        [(1, _square(0, 0, 0), []), (2, _square(0, 0, 100), [])],
    )
    nav = NavMesh(nav_path)
    assert nav.find_area((0.5, 0.5, 5.0)) == 1
    assert nav.find_area((0.5, 0.5, 95.0)) == 2


@pytest.mark.parametrize(
    ("area_id", "expected"),
    [(2, [1, 3]), (1, [2]), (999, [])],
    ids=["middle", "end", "unknown"],
)
def test_neighbors(chain_mesh: NavMesh, area_id, expected) -> None:
    assert chain_mesh.neighbors(area_id) == expected


@pytest.mark.parametrize(
    ("start", "end", "weight", "expected"),
    [
        (1, 3, "distance", [1, 2, 3]),
        (3, 1, "distance", [3, 2, 1]),
        (1, 1, "distance", [1]),
        (1, 3, "hops", [1, 2, 3]),
        (1, 3, "size", [1, 2, 3]),
    ],
    ids=["forward", "reverse", "same-area", "hop-weight", "size-weight"],
)
def test_find_path_by_area_id(chain_mesh: NavMesh, start, end, weight, expected) -> None:
    assert chain_mesh.find_path(start, end, weight=weight) == expected


@pytest.mark.parametrize(
    ("end", "expected"),
    [((2.5, 0.5, 0.0), [1, 2, 3]), ((100.0, 100.0, 0.0), [])],
    ids=["connected", "outside"],
)
def test_find_path_by_point(chain_mesh: NavMesh, end, expected) -> None:
    assert chain_mesh.find_path((0.5, 0.5, 0.0), end) == expected


def test_find_path_no_route(tmp_path: Path) -> None:
    nav_path = tmp_path / "split.nav"
    _write_nav(
        nav_path,
        [(1, _square(0, 0, 0), [2]), (2, _square(1, 0, 0), [1]), (3, _square(9, 9, 0), [])],
    )
    nav = NavMesh(nav_path)
    assert nav.find_path(1, 3) == []
    assert nav.find_path(1, 999) == []


def test_find_path_bad_weight(chain_nav: Path) -> None:
    with pytest.raises(ValueError, match="weight"):
        NavMesh(chain_nav).find_path(1, 3, weight="bogus")


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        NavMesh(tmp_path / "nope.nav")


def test_bad_nav_raises_value_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.nav"
    bad.write_bytes(b"not a nav file at all")
    with pytest.raises(ValueError):
        NavMesh(bad)


# --- map-name construction (offline; the cache is pre-populated) --------------


def _prime_cache(root: Path, version: str, map_name: str) -> Path:
    """Materialize a cached release holding one nav mesh."""
    navs = root / version / "navs"
    navs.mkdir(parents=True)
    _write_nav(navs / f"{map_name}.nav", [(1, _square(0, 0, 0), [])])
    # The extraction marker makes awpy.data treat the archive as already fetched.
    (root / version / ".navs.zip.done").touch()
    return navs / f"{map_name}.nav"


def test_map_name_uses_newest_cached_release(
    asset_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prime_cache(asset_cache, "999", "de_test")
    newest = _prime_cache(asset_cache, "2000873", "de_test")

    def boom() -> str:
        raise AssertionError("the network must not be consulted when the cache is non-empty")

    monkeypatch.setattr(data, "latest_version", boom)
    nav = NavMesh("de_test")
    assert nav.path == newest
    assert nav.area_count == 1


def test_map_name_with_pinned_version(asset_cache: Path) -> None:
    pinned = _prime_cache(asset_cache, "999", "de_test")
    _prime_cache(asset_cache, "2000873", "de_test")
    nav = NavMesh("de_test", version=999)
    assert nav.path == pinned


def test_unknown_map_raises(asset_cache: Path) -> None:
    _prime_cache(asset_cache, "999", "de_test")
    with pytest.raises(FileNotFoundError):
        NavMesh("de_missing")


@pytest.mark.parametrize("as_string", [False, True], ids=["path", "string"])
def test_version_with_file_path_raises(chain_nav: Path, as_string: bool) -> None:
    path = str(chain_nav) if as_string else chain_nav
    with pytest.raises(ValueError, match="version"):
        NavMesh(path, version=2000873)
