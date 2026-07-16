"""Acquire and cache the demo fixtures listed in ``fixtures/manifest.json``.

Fixtures are large CS2 demos hosted as GitHub release assets in the
`awpy-fixtures <https://github.com/pnxenopoulos/awpy-fixtures>`_ repo. This
module downloads them on demand, verifies each against the SHA-256 in the
manifest, and caches them under ``$AWPY_FIXTURES_DIR`` (default
``~/.cache/awpy-fixtures``).

Downloading is **opt-in**: a demo that is not already cached is only fetched
when ``AWPY_RUN_FIXTURES`` is set, so a plain ``pytest`` run never pulls ~1.5 GB
— the ground-truth tests just skip.

``fixtures/manifest.json`` is vendored from the awpy-fixtures repo (its single
source of truth). Re-sync after adding a fixture::

    curl -sfL https://raw.githubusercontent.com/pnxenopoulos/awpy-fixtures/main/manifest.json \\
      -o tests/fixtures/manifest.json
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path

from awpy import Demo

MANIFEST_PATH = Path(__file__).parent / "fixtures" / "manifest.json"


def cache_dir() -> Path:
    """Directory demos are cached in (override with ``AWPY_FIXTURES_DIR``)."""
    default = Path.home() / ".cache" / "awpy-fixtures"
    return Path(os.environ.get("AWPY_FIXTURES_DIR", default))


def download_enabled() -> bool:
    """Whether missing fixtures may be fetched (opt-in via ``AWPY_RUN_FIXTURES``)."""
    return os.environ.get("AWPY_RUN_FIXTURES", "").lower() not in ("", "0", "false", "no")


def load_manifest() -> list[dict]:
    """The fixture entries from the vendored manifest (empty if it is absent)."""
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text()).get("fixtures", [])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "awpy-fixtures"})
    with urllib.request.urlopen(request, timeout=60) as response, dest.open("wb") as handle:
        shutil.copyfileobj(response, handle, 1 << 20)


def ensure_demo(entry: dict) -> Path | None:
    """Return a verified local path to the demo, or ``None`` if unavailable.

    A cached copy is reused when its checksum matches. Otherwise the demo is
    downloaded — only when :func:`download_enabled` — and verified. A checksum
    mismatch raises (a wrong/corrupt asset is a hard error); a network failure
    (offline, or the release is not published yet) returns ``None`` so callers
    can skip.
    """
    dest = cache_dir() / entry["asset"]
    if dest.exists():
        if _sha256(dest) == entry["sha256"]:
            return dest
        dest.unlink()  # stale or corrupt — re-fetch
    if not download_enabled():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    try:
        _download(entry["url"], partial)
    except OSError:
        partial.unlink(missing_ok=True)
        return None
    digest = _sha256(partial)
    if digest != entry["sha256"]:
        partial.unlink(missing_ok=True)
        msg = f"checksum mismatch for {entry['asset']}: expected {entry['sha256']}, got {digest}"
        raise ValueError(msg)
    partial.replace(dest)
    return dest


_DEMOS: dict[str, Demo | None] = {}


def get_demo(entry: dict) -> Demo | None:
    """Parsed :class:`~awpy.Demo` for an entry, cached per session; ``None`` if unavailable."""
    name = entry["name"]
    if name not in _DEMOS:
        path = ensure_demo(entry)
        _DEMOS[name] = Demo(path) if path is not None else None
    return _DEMOS[name]


def main() -> None:
    """Pre-fetch every fixture (e.g. CI cache warming): ``python tests/fixture_store.py``."""
    os.environ["AWPY_RUN_FIXTURES"] = "1"
    for entry in load_manifest():
        path = ensure_demo(entry)
        print(f"{'ok  ' if path is not None else 'FAIL'} {entry['name']}")


if __name__ == "__main__":
    main()
