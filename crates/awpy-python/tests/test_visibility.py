"""Tests for the VisibilityChecker line-of-sight class."""

import struct
from pathlib import Path

import pytest
from awpy import VisibilityChecker, data


def _write_wall_mesh(path: Path) -> None:
    """Write one wall quad (x=0 plane, y,z in [-10, 10]) as an awpy ``.mesh``."""
    verts = [(0, -10, -10), (0, 10, -10), (0, 10, 10), (0, -10, 10)]
    tris = [(0, 1, 2), (0, 2, 3)]
    buf = bytearray(b"AWMH")
    buf += struct.pack("<III", 1, len(verts), len(tris))  # version, n_verts, n_tris
    for v in verts:
        buf += struct.pack("<fff", *v)
    for t in tris:
        buf += struct.pack("<III", *t)
    path.write_bytes(buf)


def test_wall_blocks_line_of_sight(tmp_path: Path) -> None:
    mesh = tmp_path / "wall.mesh"
    _write_wall_mesh(mesh)
    vc = VisibilityChecker(mesh)

    assert vc.triangle_count == 2
    assert vc.path == mesh
    # Straight through the wall: blocked.
    assert not vc.is_visible((-5, 0, 0), (5, 0, 0))
    assert vc.is_occluded((-5, 0, 0), (5, 0, 0))
    # Same side of the wall: clear.
    assert vc.is_visible((-5, 0, 0), (-5, 5, 0))
    assert not vc.is_occluded((-5, 0, 0), (-5, 5, 0))


def test_accepts_lists_and_tuples(tmp_path: Path) -> None:
    mesh = tmp_path / "wall.mesh"
    _write_wall_mesh(mesh)
    vc = VisibilityChecker(mesh)
    assert vc.is_visible([-5, 0, 0], [-5, 5, 0]) == vc.is_visible((-5, 0, 0), (-5, 5, 0))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        VisibilityChecker(tmp_path / "nope.mesh")


def test_bad_mesh_raises_value_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mesh"
    bad.write_bytes(b"not a mesh at all")
    with pytest.raises(ValueError):
        VisibilityChecker(bad)


# --- map-name construction (offline; the cache is pre-populated) --------------


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the asset cache to a temp dir and reset the latest-version cache."""
    monkeypatch.setattr(data, "AWPY_DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_latest_cache", None)
    return tmp_path


def _prime_cache(root: Path, version: str, map_name: str) -> Path:
    """Materialize a cached release holding one geometry mesh."""
    geometry = root / version / "geometry"
    geometry.mkdir(parents=True)
    _write_wall_mesh(geometry / f"{map_name}.mesh")
    # The extraction marker makes awpy.data treat the archive as already fetched.
    (root / version / ".geometry.zip.done").touch()
    return geometry / f"{map_name}.mesh"


def test_map_name_uses_newest_cached_release(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prime_cache(cache, "999", "de_test")
    newest = _prime_cache(cache, "2000873", "de_test")

    def boom() -> str:
        raise AssertionError("the network must not be consulted when the cache is non-empty")

    monkeypatch.setattr(data, "latest_version", boom)
    vc = VisibilityChecker("de_test")
    assert vc.path == newest
    assert vc.triangle_count == 2


def test_map_name_with_pinned_version(cache: Path) -> None:
    pinned = _prime_cache(cache, "999", "de_test")
    _prime_cache(cache, "2000873", "de_test")
    vc = VisibilityChecker("de_test", version=999)
    assert vc.path == pinned


def test_unknown_map_raises(cache: Path) -> None:
    _prime_cache(cache, "999", "de_test")
    with pytest.raises(FileNotFoundError):
        VisibilityChecker("de_missing")


def test_version_with_file_path_raises(tmp_path: Path) -> None:
    mesh = tmp_path / "wall.mesh"
    _write_wall_mesh(mesh)
    with pytest.raises(ValueError, match="version"):
        VisibilityChecker(mesh, version=2000873)
    with pytest.raises(ValueError, match="version"):
        VisibilityChecker(str(mesh), version=2000873)
