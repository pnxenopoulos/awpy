"""Download and cache versioned CS2 assets from ``awpy-data``.

Assets include collision meshes, nav meshes, radar images, and coordinate tables.
The cache is ``~/.awpy/<ClientVersion>/``. Set ``AWPY_DATA_DIR`` to change its root.

Path helpers download missing assets and return local paths.
Set ``version=`` to select a release. Otherwise, use the newest cached release,
or the latest release if the cache is empty.
Use :func:`update` or ``awpy get`` to check for updates.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

__all__ = [
    "AWPY_DATA_DIR",
    "DATA_REPO",
    "available_maps",
    "clear",
    "data_dir",
    "latest_version",
    "local_versions",
    "manifest",
    "map_data",
    "mesh_path",
    "nav_path",
    "radar_path",
    "resolve_version",
    "update",
]

#: GitHub repository the assets are published from.
DATA_REPO = "pnxenopoulos/awpy-data"

_DOWNLOAD_URL = "https://github.com/{repo}/releases/download/{version}/{name}"
_LATEST_API = "https://api.github.com/repos/{repo}/releases/latest"
_USER_AGENT = "awpy"


def _default_data_dir() -> Path:
    """Select the Awpy cache root from the environment or home directory.

    Returns:
        The expanded ``AWPY_DATA_DIR`` path, or ``~/.awpy``.
    """
    env = os.environ.get("AWPY_DATA_DIR")
    return Path(env).expanduser() if env else Path.home() / ".awpy"


#: Root of the local asset cache. Read at call time, so tests (or callers) may
#: reassign ``awpy.data.AWPY_DATA_DIR`` to redirect the cache.
AWPY_DATA_DIR = _default_data_dir()

# The per-map asset kinds and how each is packaged in a release. ``zip`` is the
# release asset that carries them; files end up at ``<version>/<subdir>/<map><ext>``.
_KIND = {
    "geometry": {"zip": "geometry.zip", "subdir": "geometry", "ext": ".mesh"},
    "nav": {"zip": "navs.zip", "subdir": "navs", "ext": ".nav"},
    "radar": {"zip": "images.zip", "subdir": "radars", "ext": ".png"},
}

# images.zip already stores members under a ``radars/`` prefix; the other
# archives are flat, so they extract into ``<version>/<subdir>/``.
_ZIP_HAS_PREFIX = {"images.zip"}

# The plain (unzipped) JSON assets published alongside the archives.
_JSON_ASSETS = ("manifest.json", "map_data.json")

# Process-lifetime cache of the resolved "latest" release tag, so repeated
# helper calls don't each hit the GitHub API.
_latest_cache: str | None = None


# --- version resolution ------------------------------------------------------


def latest_version() -> str:
    """Read the latest awpy-data release tag from GitHub.

    Returns:
        The ClientVersion tag as a string.

    Raises:
        urllib.error.URLError: If the network or GitHub API request fails.
        RuntimeError: If the response has no release tag.

    Notes:
        The successful result is cached for this Python process.
    """
    global _latest_cache
    if _latest_cache is not None:
        return _latest_cache
    req = urllib.request.Request(
        _LATEST_API.format(repo=DATA_REPO),
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as resp:  # noqa: S310 - fixed https host
        payload = json.load(resp)
    tag = payload.get("tag_name")
    if not tag:
        raise RuntimeError(f"could not determine the latest {DATA_REPO} release")
    _latest_cache = str(tag)
    return _latest_cache


def local_versions() -> list[str]:
    """List cached awpy-data version directories.

    Returns:
        Version names, oldest first; numeric names use numeric order.
    """
    if not AWPY_DATA_DIR.is_dir():
        return []
    versions = [p.name for p in AWPY_DATA_DIR.iterdir() if p.is_dir()]
    # ClientVersions are increasing integers; sort numerically when we can.
    return sorted(versions, key=lambda v: (0, int(v)) if v.isdigit() else (1, v))


def resolve_version(version: int | None = None) -> str:
    """Select an awpy-data release without downloading its assets.

    Args:
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The selected release tag as a string.

    Notes:
        An explicit version does not make a network request. An empty cache can require a GitHub API
        request.
    """
    if version is not None:
        return str(version)
    local = local_versions()
    if local:
        return local[-1]
    return latest_version()


def data_dir(version: int | None = None) -> Path:
    """Get the local directory for an awpy-data release.

    Args:
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The release path. This call does not create the directory or download assets.
    """
    return AWPY_DATA_DIR / resolve_version(version)


# --- downloading -------------------------------------------------------------


def _download(url: str, dest: Path) -> Path:
    """Download an asset and replace its destination after success.

    Args:
        url: HTTPS asset URL.
        dest: Local destination file.

    Returns:
        The destination path.

    Raises:
        FileNotFoundError: If the server returns HTTP 404.
        urllib.error.URLError: If the download fails.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    tmp = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(req) as resp, tmp.open("wb") as fh:  # noqa: S310
            shutil.copyfileobj(resp, fh)
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        if exc.code == 404:
            raise FileNotFoundError(f"no such asset in {DATA_REPO}: {url}") from exc
        raise
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, dest)
    return dest


def _ensure_json(version: str, name: str) -> Path:
    """Download a missing awpy-data JSON asset.

    Args:
        version: Release tag.
        name: JSON filename in the release.

    Returns:
        The cached JSON path.
    """
    path = AWPY_DATA_DIR / version / name
    if not path.exists():
        _download(_DOWNLOAD_URL.format(repo=DATA_REPO, version=version, name=name), path)
    return path


def _safe_extract(zf: zipfile.ZipFile, root: Path) -> None:
    """Extract archive members within the requested directory.

    Args:
        zf: Open ZIP archive.
        root: Destination directory.

    Raises:
        ValueError: If a member resolves outside the destination.
    """
    root = root.resolve()
    for info in zf.infolist():
        target = (root / info.filename).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"unsafe path in archive: {info.filename}")
    zf.extractall(root)


def _ensure_zip(version: str, kind: str, *, force: bool = False) -> Path:
    """Download and extract an awpy-data asset archive.

    Args:
        version: Release tag.
        kind: Asset kind: ``geometry``, ``nav``, or ``radar``.
        force: Download again even if the extraction marker exists.

    Returns:
        The extracted asset directory.
    """
    spec = _KIND[kind]
    version_dir = AWPY_DATA_DIR / version
    dest = version_dir / spec["subdir"]
    marker = version_dir / f".{spec['zip']}.done"
    if marker.exists() and not force:
        return dest

    version_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = _download(
            _DOWNLOAD_URL.format(repo=DATA_REPO, version=version, name=spec["zip"]),
            Path(tmpdir) / spec["zip"],
        )
        # Prefixed archives (images.zip) already contain the subdir; flat ones
        # extract straight into it.
        root = version_dir if spec["zip"] in _ZIP_HAS_PREFIX else dest
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            _safe_extract(zf, root)
    marker.touch()
    return dest


def _asset_path(kind: str, map_name: str, version: int | None) -> Path:
    """Find a map asset and download its archive if needed.

    Args:
        kind: Asset kind: ``geometry``, ``nav``, or ``radar``.
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The existing local asset path.

    Raises:
        FileNotFoundError: If the release has no matching asset.
    """
    tag = resolve_version(version)
    spec = _KIND[kind]
    dest = _ensure_zip(tag, kind)
    path = dest / f"{map_name}{spec['ext']}"
    if not path.exists():
        raise FileNotFoundError(f"no {kind} asset for '{map_name}' in {DATA_REPO} {tag}")
    return path


# --- public accessors --------------------------------------------------------


def mesh_path(map_name: str, version: int | None = None) -> Path:
    """Get a CS2 collision .mesh file from awpy-data.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The local file path. Collision geometry for ``VisibilityChecker``.

    Raises:
        FileNotFoundError: If the selected release has no matching map asset.
        urllib.error.URLError: If a required download fails.

    Notes:
        Missing assets download on demand. Cached assets can be used offline.
    """
    return _asset_path("geometry", map_name, version)


def nav_path(map_name: str, version: int | None = None) -> Path:
    """Get a CS2 navigation .nav file from awpy-data.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The local file path. Walkable areas for ``NavMesh``.

    Raises:
        FileNotFoundError: If the selected release has no matching map asset.
        urllib.error.URLError: If a required download fails.

    Notes:
        Missing assets download on demand. Cached assets can be used offline.
    """
    return _asset_path("nav", map_name, version)


def radar_path(map_name: str, version: int | None = None, *, lower: bool = False) -> Path:
    """Get a CS2 radar .png file from awpy-data.

    Args:
        map_name: CS2 map name, such as ``"de_inferno"``.
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.
        lower: Select the lower-level radar image for a map with multiple levels.

    Returns:
        The local file path. Radar background for ``awpy.plot``.

    Raises:
        FileNotFoundError: If the selected release has no matching map asset.
        urllib.error.URLError: If a required download fails.

    Notes:
        Missing assets download on demand. Cached assets can be used offline.
    """
    name = f"{map_name}_lower" if lower else map_name
    return _asset_path("radar", name, version)


def manifest(version: int | None = None) -> dict[str, Any]:
    """Read awpy-data release metadata.

    Args:
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        Version identifiers, map names, and per-file checksums as a dictionary.

    Notes:
        A missing JSON file downloads on demand.
    """
    return json.loads(_ensure_json(resolve_version(version), "manifest.json").read_text())


def map_data(version: int | None = None) -> dict[str, Any]:
    """Read CS2 world-to-radar transforms from awpy-data.

    Args:
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        Map names mapped to coordinate transforms and vertical sections.

    Notes:
        A missing JSON file downloads on demand.
    """
    return json.loads(_ensure_json(resolve_version(version), "map_data.json").read_text())


def available_maps(version: int | None = None) -> list[str]:
    """List CS2 maps in an awpy-data release.

    Args:
        version: awpy-data ClientVersion. Use the newest cached release when omitted; download the
            latest release if the cache is empty.

    Returns:
        The map names from the release manifest.

    Notes:
        A missing JSON file downloads on demand.
    """
    return list(manifest(version).get("maps", []))


def update(version: int | None = None, *, force: bool = False) -> Path:
    """Download every asset for an awpy-data release.

    Args:
        version: ClientVersion to install. Omit it to query the latest GitHub release.
        force: Delete this release cache and download it again.

    Returns:
        The local release directory.

    Raises:
        FileNotFoundError: If a required release asset does not exist.
        urllib.error.URLError: If a required download fails.

    Notes:
        This update operation checks the latest release when no version is supplied. Read helpers
        instead prefer the newest cached release.
    """
    tag = str(version) if version is not None else latest_version()
    if force and (AWPY_DATA_DIR / tag).exists():
        shutil.rmtree(AWPY_DATA_DIR / tag)
    for name in _JSON_ASSETS:
        _ensure_json(tag, name)
    for kind in _KIND:
        _ensure_zip(tag, kind, force=force)
    return AWPY_DATA_DIR / tag


def clear(version: int | None = None) -> None:
    """Delete cached awpy-data assets.

    Args:
        version: ClientVersion to delete. Omit it to delete the entire asset cache.

    Raises:
        OSError: If the cache cannot be removed.
    """
    target = AWPY_DATA_DIR / str(version) if version is not None else AWPY_DATA_DIR
    if target.exists():
        shutil.rmtree(target)
