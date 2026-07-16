"""Download and cache the CS2 map assets published by the ``awpy-data`` project.

Awpy's map assets — collision meshes for line-of-sight, radar images, nav
meshes, and the world→radar coordinate table — are built from a clean CS2
install and published as GitHub Releases at
`pnxenopoulos/awpy-data <https://github.com/pnxenopoulos/awpy-data>`_. Each
release is pinned to the game's ``ClientVersion`` (e.g. ``2000873``).

This module fetches those assets on demand and caches them under
``$HOME/.awpy/<version>/`` (override the root with the ``AWPY_DATA_DIR``
environment variable)::

    $HOME/.awpy/2000873/
        manifest.json          version identifiers + per-file checksums
        map_data.json          per-map world->radar transform
        radars/<map>.png       radar image (+ <map>_lower.png for Nuke/Vertigo/Train)
        navs/<map>.nav         nav mesh
        geometry/<map>.mesh    collision mesh for VisibilityChecker

The path helpers download whatever they need the first time and return a local
path, so a collision mesh for line-of-sight is one call away::

    from awpy import VisibilityChecker, data

    vc = VisibilityChecker(data.mesh_path("de_inferno"))
    vc.is_visible((1258.04, 455.47, 181.22), (-158.62, 819.09, 103.73))

Pass ``version=`` to pin a specific release; omit it to use the newest release
already in the cache (the latest release is fetched only when the cache is
empty). Move the cache forward explicitly with :func:`update` or ``awpy get``.
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
    """Return the tag of the most recent ``awpy-data`` release (a ClientVersion).

    Queries the GitHub API (once per process; the result is cached). Raises on
    a network or API failure.
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
    """Version directories already present in the cache, oldest first."""
    if not AWPY_DATA_DIR.is_dir():
        return []
    versions = [p.name for p in AWPY_DATA_DIR.iterdir() if p.is_dir()]
    # ClientVersions are increasing integers; sort numerically when we can.
    return sorted(versions, key=lambda v: (0, int(v)) if v.isdigit() else (1, v))


def resolve_version(version: int | None = None) -> str:
    """Resolve ``version`` to a concrete release tag.

    A given ``version`` is returned as-is (stringified). ``None`` resolves to
    the newest release already in the cache — no network involved — so pinned
    analyses keep working offline and don't shift under you mid-session. Only
    an empty cache falls through to the latest GitHub release. Move the cache
    forward explicitly with :func:`update` (or ``awpy get``).
    """
    if version is not None:
        return str(version)
    local = local_versions()
    if local:
        return local[-1]
    return latest_version()


def data_dir(version: int | None = None) -> Path:
    """Local cache directory for a release (resolving ``None`` to the latest)."""
    return AWPY_DATA_DIR / resolve_version(version)


# --- downloading -------------------------------------------------------------


def _download(url: str, dest: Path) -> Path:
    """Download ``url`` to ``dest`` atomically, returning ``dest``."""
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
    """Ensure a plain JSON asset is cached locally; return its path."""
    path = AWPY_DATA_DIR / version / name
    if not path.exists():
        _download(_DOWNLOAD_URL.format(repo=DATA_REPO, version=version, name=name), path)
    return path


def _safe_extract(zf: zipfile.ZipFile, root: Path) -> None:
    """Extract all members under ``root``, rejecting path-traversal entries."""
    root = root.resolve()
    for info in zf.infolist():
        target = (root / info.filename).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"unsafe path in archive: {info.filename}")
    zf.extractall(root)


def _ensure_zip(version: str, kind: str, *, force: bool = False) -> Path:
    """Ensure a kind's archive is downloaded and extracted; return its subdir."""
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
    tag = resolve_version(version)
    spec = _KIND[kind]
    dest = _ensure_zip(tag, kind)
    path = dest / f"{map_name}{spec['ext']}"
    if not path.exists():
        raise FileNotFoundError(f"no {kind} asset for '{map_name}' in {DATA_REPO} {tag}")
    return path


# --- public accessors --------------------------------------------------------


def mesh_path(map_name: str, version: int | None = None) -> Path:
    """Local path to a map's collision ``.mesh`` (for :class:`~awpy.VisibilityChecker`)."""
    return _asset_path("geometry", map_name, version)


def nav_path(map_name: str, version: int | None = None) -> Path:
    """Local path to a map's ``.nav`` mesh."""
    return _asset_path("nav", map_name, version)


def radar_path(map_name: str, version: int | None = None, *, lower: bool = False) -> Path:
    """Local path to a map's radar ``.png``.

    Set ``lower=True`` for the lower level of a multi-level map (Nuke, Vertigo,
    Train).
    """
    name = f"{map_name}_lower" if lower else map_name
    return _asset_path("radar", name, version)


def manifest(version: int | None = None) -> dict:
    """The release manifest (version identifiers + per-file checksums) as a dict."""
    return json.loads(_ensure_json(resolve_version(version), "manifest.json").read_text())


def map_data(version: int | None = None) -> dict:
    """The per-map world→radar coordinate table (``map_data.json``) as a dict."""
    return json.loads(_ensure_json(resolve_version(version), "map_data.json").read_text())


def available_maps(version: int | None = None) -> list[str]:
    """Map names shipped in a release (from the manifest's ``maps`` list)."""
    return list(manifest(version).get("maps", []))


def update(version: int | None = None, *, force: bool = False) -> Path:
    """Download every asset for a release into the cache; return its directory.

    Unlike the read helpers, ``version=None`` here means the latest GitHub
    release — this is the "check for updates" entry point — not the newest
    cached one. With ``force=True``, re-download even if already cached.
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
    """Delete cached assets — one release, or the whole cache if ``version`` is None."""
    target = AWPY_DATA_DIR / str(version) if version is not None else AWPY_DATA_DIR
    if target.exists():
        shutil.rmtree(target)
