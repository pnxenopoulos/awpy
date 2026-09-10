"""Tests for the NavMesh navigation-mesh class."""

import struct
from pathlib import Path

import pytest
from awpy import NavMesh, data

# A unit square in the XY plane at height ``z``, as four ordered corners.
Square = list[tuple[float, float, float]]


def _square(x: float, y: float, z: float) -> Square:
    return [(x, y, z), (x + 1, y, z), (x + 1, y + 1, z), (x, y + 1, z)]


def _write_nav(path: Path, areas: list[tuple[int, Square, list[int]]]) -> None:
    """Write a minimal version-35 ``.nav`` file.

    Each area is ``(area_id, four_corners, connection_area_ids)``; every area is
    one 4-corner polygon and all its connections are placed on the first edge.
    """
    buf = bytearray()
    buf += struct.pack("<I", 0xFEEDFACE)  # magic
    buf += struct.pack("<III", 35, 1, 1)  # version, sub_version, unk1 (analyzed)

    # Shared polygon table: four corners per area.
    buf += struct.pack("<I", len(areas) * 4)
    for _, corners, _ in areas:
        for cx, cy, cz in corners:
            buf += struct.pack("<fff", cx, cy, cz)
    buf += struct.pack("<I", len(areas))  # polygon_count
    for i in range(len(areas)):
        buf += struct.pack("<B", 4)  # corner count
        for k in range(4):
            buf += struct.pack("<I", i * 4 + k)
        buf += struct.pack("<I", 0)  # version>=35 per-polygon field

    buf += struct.pack("<I", 0)  # version>=32 field
    buf += struct.pack("<I", 0)  # version>=35 field

    buf += struct.pack("<I", len(areas))  # area_count
    for i, (area_id, _, conns) in enumerate(areas):
        buf += struct.pack("<I", area_id)
        buf += struct.pack("<q", 0)  # dynamic_attribute_flags
        buf += struct.pack("<B", 0)  # hull_index
        buf += struct.pack("<I", i)  # polygon_index
        buf += struct.pack("<I", 0)  # skip
        buf += struct.pack("<I", len(conns))  # connections on first edge
        for c in conns:
            buf += struct.pack("<II", c, 0)  # neighbor area id, edge id
        for _ in range(3):
            buf += struct.pack("<I", 0)  # no connections on the other edges
        buf += b"\x00" * 5  # legacy hiding/encounter counts
        buf += struct.pack("<I", 0)  # ladders_above count
        buf += struct.pack("<I", 0)  # ladders_below count
    path.write_bytes(buf)


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


def test_parses_header_and_areas(chain_nav: Path) -> None:
    nav = NavMesh(chain_nav)
    assert nav.path == chain_nav
    assert len(nav) == 3
    assert nav.area_count == 3
    assert nav.version == 35
    assert nav.sub_version == 1
    assert nav.is_analyzed is True
    assert "areas=3" in repr(nav)


def test_areas_dataframe(chain_nav: Path) -> None:
    df = NavMesh(chain_nav).areas
    assert df.shape == (3, 9)
    assert df.columns == [
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
    assert df["area_id"].to_list() == [1, 2, 3]
    assert df["n_corners"].to_list() == [4, 4, 4]
    # Area 2 connects to both neighbours; the ends connect to one each.
    assert df["n_connections"].to_list() == [1, 2, 1]
    # Unit square -> centroid at (0.5, 0.5) and area 1.0.
    assert df["size"].to_list() == pytest.approx([1.0, 1.0, 1.0])


def test_area_detail(chain_nav: Path) -> None:
    nav = NavMesh(chain_nav)
    a = nav.area(2)
    assert a is not None
    assert a["area_id"] == 2
    assert a["connections"] == [1, 3]
    assert len(a["corners"]) == 4
    assert a["centroid"] == pytest.approx((1.5, 0.5, 0.0))
    assert a["size"] == pytest.approx(1.0)
    assert a["ladders_above"] == []
    assert nav.area(999) is None


def test_find_area(chain_nav: Path) -> None:
    nav = NavMesh(chain_nav)
    assert nav.find_area((0.5, 0.5, 0.0)) == 1
    assert nav.find_area((1.5, 0.5, 0.0)) == 2
    assert nav.find_area((2.5, 0.5, 0.0)) == 3
    # Over no area.
    assert nav.find_area((100.0, 100.0, 0.0)) is None


def test_find_area_disambiguates_by_height(tmp_path: Path) -> None:
    nav_path = tmp_path / "stacked.nav"
    _write_nav(
        nav_path,
        [(1, _square(0, 0, 0), []), (2, _square(0, 0, 100), [])],
    )
    nav = NavMesh(nav_path)
    assert nav.find_area((0.5, 0.5, 5.0)) == 1
    assert nav.find_area((0.5, 0.5, 95.0)) == 2


def test_neighbors(chain_nav: Path) -> None:
    nav = NavMesh(chain_nav)
    assert nav.neighbors(2) == [1, 3]
    assert nav.neighbors(1) == [2]
    assert nav.neighbors(999) == []


def test_find_path_by_area_id(chain_nav: Path) -> None:
    nav = NavMesh(chain_nav)
    assert nav.find_path(1, 3) == [1, 2, 3]
    assert nav.find_path(3, 1) == [3, 2, 1]
    assert nav.find_path(1, 1) == [1]
    assert nav.find_path(1, 3, weight="hops") == [1, 2, 3]
    assert nav.find_path(1, 3, weight="size") == [1, 2, 3]


def test_find_path_by_point(chain_nav: Path) -> None:
    nav = NavMesh(chain_nav)
    assert nav.find_path((0.5, 0.5, 0.0), (2.5, 0.5, 0.0)) == [1, 2, 3]
    # A point over no area -> empty path.
    assert nav.find_path((0.5, 0.5, 0.0), (100.0, 100.0, 0.0)) == []


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


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the asset cache to a temp dir and reset the latest-version cache."""
    monkeypatch.setattr(data, "AWPY_DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_latest_cache", None)
    return tmp_path


def _prime_cache(root: Path, version: str, map_name: str) -> Path:
    """Materialize a cached release holding one nav mesh."""
    navs = root / version / "navs"
    navs.mkdir(parents=True)
    _write_nav(navs / f"{map_name}.nav", [(1, _square(0, 0, 0), [])])
    # The extraction marker makes awpy.data treat the archive as already fetched.
    (root / version / ".navs.zip.done").touch()
    return navs / f"{map_name}.nav"


def test_map_name_uses_newest_cached_release(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prime_cache(cache, "999", "de_test")
    newest = _prime_cache(cache, "2000873", "de_test")

    def boom() -> str:
        raise AssertionError("the network must not be consulted when the cache is non-empty")

    monkeypatch.setattr(data, "latest_version", boom)
    nav = NavMesh("de_test")
    assert nav.path == newest
    assert nav.area_count == 1


def test_map_name_with_pinned_version(cache: Path) -> None:
    pinned = _prime_cache(cache, "999", "de_test")
    _prime_cache(cache, "2000873", "de_test")
    nav = NavMesh("de_test", version=999)
    assert nav.path == pinned


def test_unknown_map_raises(cache: Path) -> None:
    _prime_cache(cache, "999", "de_test")
    with pytest.raises(FileNotFoundError):
        NavMesh("de_missing")


def test_version_with_file_path_raises(chain_nav: Path) -> None:
    with pytest.raises(ValueError, match="version"):
        NavMesh(chain_nav, version=2000873)
    with pytest.raises(ValueError, match="version"):
        NavMesh(str(chain_nav), version=2000873)
