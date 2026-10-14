import re
from pathlib import Path

project = "Awpy"
author = "Peter Xenopoulos"
copyright = "2026, Peter Xenopoulos"

# Read the version from the workspace Cargo.toml (single source of truth). The
# awpy-python crate inherits `version.workspace = true`, so the literal lives in
# the workspace root manifest, three levels up from this file.
_cargo_toml = Path(__file__).resolve().parents[3] / "Cargo.toml"
_match = re.search(
    r'^\s*\[workspace\.package\][^[]*?^version\s*=\s*"(.+?)"',
    _cargo_toml.read_text(),
    re.MULTILINE | re.DOTALL,
)
version = _match.group(1) if _match else "0.0.0"
release = version

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    # The docstrings are Google style ("Args:" / "Returns:" / "Raises:").
    "sphinx.ext.napoleon",
]
# Deliberately no `intersphinx`: it fetches inventories over the network at build
# time, and this build runs with `-W`, so a flaky fetch would fail CI.

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# ── autodoc ─────────────────────────────────────────────────────────────────
# The API reference is generated from the docstrings rather than written by hand,
# so it cannot drift from what the package actually exposes. `Demo`,
# `VisibilityChecker` and `NavMesh` live in the compiled `awpy._awpy` extension,
# so **the docs build must import a built awpy** (see .readthedocs.yaml and the
# `docs` CI job) — autodoc reads docstrings off the live objects, not the `.pyi`.
autodoc_member_order = "bysource"
# Keep annotations in the signature. "description" rewrites the napoleon-generated
# field list to merge types in, which produces malformed rST for the compiled
# functions (they have no annotations to merge).
autodoc_typehints = "signature"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": False,
}
# PyO3 getters and methods carry no Python annotations, so autodoc has no types to
# read; method signatures come from `#[pyo3(text_signature = ...)]` in
# crates/awpy-python/src/lib.rs, and property types are stated in the docstrings.
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_rtype = False
# Render an `Attributes:` section as an `:ivar:` field list rather than separate
# `.. attribute::` directives. For an annotated dataclass those directives collide
# with the fields autodoc already picks up, and every attribute is reported twice.
napoleon_use_ivar = True

# ── Theme: shibuya ──────────────────────────────────────────────────────────
# Dark is the default; the toggle still offers light/auto because shibuya reads
# `localStorage._theme || color_mode`. The "amber" accent is a Radix color scale
# that stays consistent and accessible across both modes — an AWP / CS gold that
# suits the project's name.
html_theme = "shibuya"
html_static_path = ["_static"]
html_favicon = "_static/favicon.ico"
html_logo = "_static/logo.svg"
html_css_files = ["custom.css"]
html_title = "Awpy"

html_theme_options = {
    "color_mode": "dark",
    "accent_color": "amber",
    "github_url": "https://github.com/pnxenopoulos/awpy",
    "nav_links": [
        {"title": "Getting started", "url": "getting-started"},
        {"title": "Datasets", "url": "datasets"},
        {"title": "API", "url": "api"},
        {"title": "CLI", "url": "cli"},
    ],
}
