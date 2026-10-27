"""Tests for the VisibilityChecker line-of-sight class."""

import array
import random
from pathlib import Path

import polars as pl
import pytest
from awpy import VisibilityChecker, data
from spatial_fixtures import write_mesh


def _write_wall_mesh(path: Path) -> None:
    """Write one wall quad (x=0 plane, y,z in [-10, 10]) as an awpy ``.mesh``."""
    verts = [(0, -10, -10), (0, 10, -10), (0, 10, 10), (0, -10, 10)]
    tris = [(0, 1, 2), (0, 2, 3)]
    write_mesh(path, verts, tris)


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


def _prime_cache(root: Path, version: str, map_name: str) -> Path:
    """Materialize a cached release holding one geometry mesh."""
    geometry = root / version / "geometry"
    geometry.mkdir(parents=True)
    _write_wall_mesh(geometry / f"{map_name}.mesh")
    # The extraction marker makes awpy.data treat the archive as already fetched.
    (root / version / ".geometry.zip.done").touch()
    return geometry / f"{map_name}.mesh"


def test_map_name_uses_newest_cached_release(
    asset_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prime_cache(asset_cache, "999", "de_test")
    newest = _prime_cache(asset_cache, "2000873", "de_test")

    def boom() -> str:
        raise AssertionError("the network must not be consulted when the cache is non-empty")

    monkeypatch.setattr(data, "latest_version", boom)
    vc = VisibilityChecker("de_test")
    assert vc.path == newest
    assert vc.triangle_count == 2


def test_map_name_with_pinned_version(asset_cache: Path) -> None:
    pinned = _prime_cache(asset_cache, "999", "de_test")
    _prime_cache(asset_cache, "2000873", "de_test")
    vc = VisibilityChecker("de_test", version=999)
    assert vc.path == pinned


def test_unknown_map_raises(asset_cache: Path) -> None:
    _prime_cache(asset_cache, "999", "de_test")
    with pytest.raises(FileNotFoundError):
        VisibilityChecker("de_missing")


def test_version_with_file_path_raises(tmp_path: Path) -> None:
    mesh = tmp_path / "wall.mesh"
    _write_wall_mesh(mesh)
    with pytest.raises(ValueError, match="version"):
        VisibilityChecker(mesh, version=2000873)
    with pytest.raises(ValueError, match="version"):
        VisibilityChecker(str(mesh), version=2000873)


# --- batch queries ------------------------------------------------------------


def _wall_checker(tmp_path: Path) -> VisibilityChecker:
    mesh = tmp_path / "wall.mesh"
    _write_wall_mesh(mesh)
    return VisibilityChecker(mesh)


def _random_points(n: int, seed: int) -> list[tuple[float, float, float]]:
    """Points around the wall; every third is snapped to whole units, so some
    segments end on the wall or graze its edges."""
    rng = random.Random(seed)
    points = []
    for i in range(n):
        p = (rng.uniform(-20, 20), rng.uniform(-20, 20), rng.uniform(-20, 20))
        points.append(tuple(float(round(c)) for c in p) if i % 3 == 0 else p)
    return points


def _buffer(points: list[tuple[float, float, float]], typecode: str) -> memoryview:
    """An ``(N, 3)`` buffer of ``points`` built without NumPy."""
    flat = array.array(typecode, [c for p in points for c in p])
    return memoryview(flat).cast("B").cast(typecode, (len(points), 3))


def test_batch_matches_single_queries(tmp_path: Path) -> None:
    vc = _wall_checker(tmp_path)
    a, b = _random_points(3000, 1), _random_points(3000, 2)
    expected = [vc.is_visible(p, q) for p, q in zip(a, b, strict=True)]
    assert True in expected and False in expected

    visible = vc.is_visible_many(a, b)
    assert isinstance(visible, pl.Series)
    assert visible.name == "visible"
    assert visible.dtype == pl.Boolean
    assert visible.to_list() == expected

    occluded = vc.is_occluded_many(a, b)
    assert occluded.name == "occluded"
    assert occluded.to_list() == [not v for v in expected]


@pytest.mark.parametrize("threads", [1, 2, 7, None])
def test_batch_shared_eye_any_thread_count(tmp_path: Path, threads: int | None) -> None:
    vc = _wall_checker(tmp_path)
    eye = (-5.0, 0.5, 0.5)
    b = _random_points(5000, 3)
    expected = [vc.is_visible(eye, q) for q in b]
    assert vc.is_visible_many(eye, b, threads=threads).to_list() == expected
    # The same eye given once per segment.
    assert vc.is_visible_many([eye] * len(b), b, threads=threads).to_list() == expected


@pytest.mark.parametrize("typecode", ["f", "d"])
def test_batch_accepts_buffers(tmp_path: Path, typecode: str) -> None:
    vc = _wall_checker(tmp_path)
    a, b = _random_points(500, 4), _random_points(500, 5)
    expected = vc.is_visible_many(a, b).to_list()
    assert vc.is_visible_many(_buffer(a, typecode), _buffer(b, typecode)).to_list() == expected
    # A one-dimensional buffer of three values is a single shared eye.
    eye = memoryview(array.array(typecode, a[0]))
    shared = vc.is_visible_many(a[0], b).to_list()
    assert vc.is_visible_many(eye, _buffer(b, typecode)).to_list() == shared


def test_batch_accepts_numpy_arrays(tmp_path: Path) -> None:
    np = pytest.importorskip("numpy")
    vc = _wall_checker(tmp_path)
    a, b = _random_points(2000, 6), _random_points(2000, 7)
    expected = vc.is_visible_many(a, b).to_list()

    a64, b64 = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    assert vc.is_visible_many(a64, b64).to_list() == expected
    a32, b32 = a64.astype(np.float32), b64.astype(np.float32)
    assert vc.is_visible_many(a32, b32).to_list() == expected
    # Strided and Fortran-ordered arrays are read row by row all the same.
    assert vc.is_visible_many(a64[::2], b64[::2]).to_list() == expected[::2]
    fortran = (np.asfortranarray(a64), np.asfortranarray(b64))
    assert vc.is_visible_many(*fortran).to_list() == expected
    # A (3,) eye and a (1, 3) eye both mean one shared start point.
    shared = vc.is_visible_many(a[0], b).to_list()
    assert vc.is_visible_many(a64[0], b64).to_list() == shared
    assert vc.is_visible_many(a64[:1], b64).to_list() == shared


def test_batch_of_zero_or_one_segment(tmp_path: Path) -> None:
    vc = _wall_checker(tmp_path)
    assert vc.is_visible_many((0, 0, 0), []).to_list() == []
    assert vc.is_occluded_many([], []).len() == 0
    assert vc.is_visible_many((-5, 0, 0), [(5, 0, 0)]).to_list() == [False]
    assert vc.is_visible_many([(-5, 0, 0)], [(-5, 5, 0)]).to_list() == [True]


def test_batch_rejects_bad_input(tmp_path: Path) -> None:
    vc = _wall_checker(tmp_path)
    eye = (0.0, 0.0, 0.0)
    b = [(5.0, 0.0, 0.0), (5.0, 1.0, 0.0)]
    with pytest.raises(ValueError, match="1 or 2 points"):
        vc.is_visible_many(b * 2, b)
    for threads in (0, -1):
        with pytest.raises(ValueError, match="threads"):
            vc.is_visible_many(eye, b, threads=threads)
    with pytest.raises(ValueError, match=r"a must have shape \(N, 3\) or \(3,\)"):
        vc.is_visible_many(memoryview(array.array("f", [0.0] * 4)).cast("B").cast("f", (2, 2)), b)
    with pytest.raises(ValueError, match=r"shape \(N, 3\)"):
        vc.is_visible_many(eye, memoryview(array.array("f", [5.0, 0.0, 0.0])))
    with pytest.raises(ValueError, match=r"shape \(N, 3\)"):
        vc.is_visible_many(eye, memoryview(array.array("f", [0.0] * 4)).cast("B").cast("f", (2, 2)))
    with pytest.raises(TypeError, match="float32 or float64"):
        vc.is_visible_many(eye, memoryview(array.array("i", [1] * 6)).cast("B").cast("i", (2, 3)))
    with pytest.raises(TypeError, match="sequence of"):
        vc.is_visible_many(eye, "not points")
