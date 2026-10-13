"""Tests for the awpy.data asset cache (offline; downloads are stubbed)."""

import json
import shutil
import zipfile
from pathlib import Path

import pytest
from awpy import data


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


@pytest.mark.parametrize("version", [2000873, "2000873"], ids=["integer", "string"])
def test_resolve_version_explicit(asset_cache: Path, version) -> None:
    assert data.resolve_version(version) == "2000873"


def test_resolve_version_prefers_cache_over_network(
    asset_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (asset_cache / "1000").mkdir()
    (asset_cache / "2000873").mkdir()

    def boom() -> str:
        raise AssertionError("the network must not be consulted when the cache is non-empty")

    monkeypatch.setattr(data, "latest_version", boom)
    assert data.resolve_version(None) == "2000873"  # newest local wins


def test_resolve_version_empty_cache_falls_through_to_latest(
    asset_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data, "latest_version", lambda: "42")
    assert data.resolve_version(None) == "42"


def test_local_versions_sorted_numerically(asset_cache: Path) -> None:
    for v in ("9", "100", "2000873"):
        (asset_cache / v).mkdir()
    assert data.local_versions() == ["9", "100", "2000873"]


def test_data_dir(asset_cache: Path) -> None:
    assert data.data_dir("2000873") == asset_cache / "2000873"


@pytest.mark.parametrize(
    ("helper", "map_name", "options", "relative_path", "contents"),
    [
        (data.mesh_path, "de_inferno", {}, "geometry/de_inferno.mesh", b"AWMH-mesh"),
        (data.nav_path, "de_inferno", {}, "navs/de_inferno.nav", b"nav"),
        (data.radar_path, "de_inferno", {}, "radars/de_inferno.png", b"png"),
        (data.radar_path, "de_nuke", {"lower": True}, "radars/de_nuke_lower.png", b"png"),
    ],
    ids=["mesh", "nav", "radar", "lower-radar"],
)
def test_path_helper_extracts_the_requested_asset(
    asset_cache: Path, stub_release: Path, helper, map_name, options, relative_path, contents
) -> None:
    path = helper(map_name, "9", **options)
    assert path == asset_cache / "9" / relative_path
    assert path.read_bytes() == contents


def test_manifest_reads_release_metadata(asset_cache: Path, stub_release: Path) -> None:
    assert data.manifest("9")["release_key"] == "9"


def test_map_data_reads_map_settings(asset_cache: Path, stub_release: Path) -> None:
    assert data.map_data("9")["de_inferno"]["scale"] == 4.9


def test_available_maps_uses_the_release_manifest(asset_cache: Path, stub_release: Path) -> None:
    assert data.available_maps("9") == ["de_inferno"]


def test_missing_map_raises(asset_cache: Path, stub_release: Path) -> None:
    with pytest.raises(FileNotFoundError):
        data.mesh_path("de_nonexistent", "9")


def test_update_installs_the_complete_release(asset_cache: Path, stub_release: Path) -> None:
    directory = data.update("9")
    assert directory == asset_cache / "9"
    assert (directory / "geometry" / "de_inferno.mesh").exists()
    assert (directory / "manifest.json").exists()


def test_clear_removes_an_installed_release(asset_cache: Path, stub_release: Path) -> None:
    data.update("9")
    data.clear("9")
    assert not (asset_cache / "9").exists()


def test_update_targets_latest_release_not_newest_cached(
    asset_cache: Path, stub_release: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (asset_cache / "5").mkdir()  # an older release is already cached
    monkeypatch.setattr(data, "latest_version", lambda: "9")
    assert data.update() == asset_cache / "9"


def test_safe_extract_rejects_traversal(asset_cache: Path) -> None:
    evil = asset_cache / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../escape.txt", b"x")
    with zipfile.ZipFile(evil) as z, pytest.raises(ValueError):
        data._safe_extract(z, asset_cache / "out")
