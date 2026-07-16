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
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

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
