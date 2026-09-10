"""Tests for the awpy.data asset cache (offline; downloads are stubbed)."""

import json
import shutil
import zipfile
from pathlib import Path

import pytest
from awpy import data


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the asset cache to a temp dir and reset the latest-version cache."""
    monkeypatch.setattr(data, "AWPY_DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "_latest_cache", None)
    return tmp_path


@pytest.fixture
def stub_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a fake release tree and make ``data._download`` serve from it."""
    src = tmp_path / "release"
    src.mkdir()
    with zipfile.ZipFile(src / "geometry.zip", "w") as z:  # flat archive
        z.writestr("de_inferno.mesh", b"AWMH-mesh")
    with zipfile.ZipFile(src / "navs.zip", "w") as z:  # flat archive
        z.writestr("de_inferno.nav", b"nav")
    with zipfile.ZipFile(src / "images.zip", "w") as z:  # radars/ prefix
        z.writestr("radars/de_inferno.png", b"png")
        z.writestr("radars/de_nuke_lower.png", b"png")
    (src / "manifest.json").write_text(json.dumps({"release_key": "9", "maps": ["de_inferno"]}))
    (src / "map_data.json").write_text(json.dumps({"de_inferno": {"scale": 4.9}}))

    def fake_download(url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src / url.rsplit("/", 1)[-1], dest)
        return dest

    monkeypatch.setattr(data, "_download", fake_download)
    return src


def test_resolve_version_explicit(cache: Path) -> None:
    assert data.resolve_version(2000873) == "2000873"
    assert data.resolve_version("2000873") == "2000873"  # strings are tolerated at runtime


def test_resolve_version_prefers_cache_over_network(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (cache / "1000").mkdir()
    (cache / "2000873").mkdir()

    def boom() -> str:
        raise AssertionError("the network must not be consulted when the cache is non-empty")

    monkeypatch.setattr(data, "latest_version", boom)
    assert data.resolve_version(None) == "2000873"  # newest local wins


def test_resolve_version_empty_cache_falls_through_to_latest(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data, "latest_version", lambda: "42")
    assert data.resolve_version(None) == "42"


def test_local_versions_sorted_numerically(cache: Path) -> None:
    for v in ("9", "100", "2000873"):
        (cache / v).mkdir()
    assert data.local_versions() == ["9", "100", "2000873"]


def test_data_dir(cache: Path) -> None:
    assert data.data_dir("2000873") == cache / "2000873"


def test_path_helpers_download_and_extract(cache: Path, stub_release: Path) -> None:
    assert data.mesh_path("de_inferno", "9").read_bytes() == b"AWMH-mesh"
    assert data.nav_path("de_inferno", "9").name == "de_inferno.nav"
    assert data.radar_path("de_inferno", "9").name == "de_inferno.png"
    assert data.radar_path("de_nuke", "9", lower=True).name == "de_nuke_lower.png"

    # Files land in the documented per-kind subdirs.
    assert data.mesh_path("de_inferno", "9").parent == cache / "9" / "geometry"
    assert data.radar_path("de_inferno", "9").parent == cache / "9" / "radars"


def test_manifest_and_map_data(cache: Path, stub_release: Path) -> None:
    assert data.manifest("9")["release_key"] == "9"
    assert data.map_data("9")["de_inferno"]["scale"] == 4.9
    assert data.available_maps("9") == ["de_inferno"]


def test_missing_map_raises(cache: Path, stub_release: Path) -> None:
    with pytest.raises(FileNotFoundError):
        data.mesh_path("de_nonexistent", "9")


def test_update_then_clear(cache: Path, stub_release: Path) -> None:
    out = data.update("9")
    assert out == cache / "9"
    assert (out / "geometry" / "de_inferno.mesh").exists()
    assert (out / "manifest.json").exists()

    data.clear("9")
    assert not (cache / "9").exists()


def test_update_targets_latest_release_not_newest_cached(
    cache: Path, stub_release: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (cache / "5").mkdir()  # an older release is already cached
    monkeypatch.setattr(data, "latest_version", lambda: "9")
    assert data.update() == cache / "9"


def test_safe_extract_rejects_traversal(cache: Path) -> None:
    evil = cache / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../escape.txt", b"x")
    with zipfile.ZipFile(evil) as z, pytest.raises(ValueError):
        data._safe_extract(z, cache / "out")
