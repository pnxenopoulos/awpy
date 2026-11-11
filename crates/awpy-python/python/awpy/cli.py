"""Inspect demos and manage map assets with ``awpy`` or ``python -m awpy``.

Use ``awpy --help`` for commands. The separate Rust binary ``awpy-dev``
provides parser-internal inspection.
"""

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import polars as pl
import typer

from awpy import Demo, InvalidDemoError, __version__, data

app = typer.Typer(
    name="awpy",
    help="Awpy — parse CS2 demos and manage map-data assets from the command line.",
    epilog="Parser-internals commands (messages, entities, send-tables, string-tables, "
    "classes) live in the Rust developer binary: cargo install --path crates/awpy-dev "
    "(installs `awpy-dev`).",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

_DEMO_PANEL = "Demo inspection"
_DATA_PANEL = "Map-data cache"

DemoArg = Annotated[
    Path, typer.Argument(help="Path to the demo file.", exists=True, dir_okay=False)
]
LimitOpt = Annotated[int | None, typer.Option("--limit", help="Maximum number of rows to display.")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Output as JSON instead of a table.")]
ReleaseArg = Annotated[int | None, typer.Argument(help="Release ClientVersion, e.g. 2000873.")]


def _version_callback(value: bool) -> None:
    """Print the Awpy version when ``--version`` is passed."""
    if value:
        typer.echo(f"awpy {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the awpy version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Parse CS2 demos and manage map assets with the Awpy CLI."""


def _load(file: Path) -> Demo:
    """Open a demo, exiting with an error message if it is invalid."""
    try:
        return Demo(file)
    except InvalidDemoError as exc:
        typer.secho(f"invalid demo file: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _emit_df(df: pl.DataFrame, *, limit: int | None = None, as_json: bool = False) -> None:
    """Print up to ``limit`` rows as JSON or as a terminal table."""
    if limit is not None:
        df = df.head(limit)
    if as_json:
        typer.echo(df.write_json())
        return
    width = shutil.get_terminal_size((160, 24)).columns
    with pl.Config(tbl_cols=-1, tbl_rows=-1, tbl_width_chars=width):
        typer.echo(df)


# --- demo inspection -----------------------------------------------------------


@app.command(rich_help_panel=_DEMO_PANEL)
def verify(file: DemoArg, as_json: JsonOpt = False) -> None:
    """Check the CS2 demo header and file signature."""
    try:
        _ = Demo(file).header  # parsing the header is the validity check
        payload = {"valid": True, "file": str(file)}
    except InvalidDemoError as exc:
        payload = {"valid": False, "file": str(file), "error": str(exc)}
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
    elif payload["valid"]:
        typer.secho(f"Valid demo file: {file}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Invalid demo file: {file}", fg=typer.colors.RED, err=True)
        typer.secho(f"  {payload['error']}", fg=typer.colors.RED, err=True)
    if not payload["valid"]:
        raise typer.Exit(1)


@app.command(rich_help_panel=_DEMO_PANEL)
def info(file: DemoArg, as_json: JsonOpt = False) -> None:
    """Print CS2 demo header and playback metadata."""
    header = _load(file).header
    if as_json:
        typer.echo(json.dumps(header, indent=2))
        return
    pad = max(len(key) for key in header)
    for key, value in header.items():
        typer.echo(f"{key:<{pad}}  {value}")


@app.command(rich_help_panel=_DEMO_PANEL)
def events(
    file: DemoArg,
    name: Annotated[
        str | None,
        typer.Argument(help="Event name to dump as a table (e.g. player_ping)."),
    ] = None,
    summary: Annotated[bool, typer.Option("--summary", help="Show per-event-name counts.")] = False,
    limit: LimitOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """List CS2 game events, counts, or rows for one event."""
    events_ = _load(file).events
    if name is not None:
        if name not in events_:
            typer.secho(
                f"no event '{name}' in this demo — `awpy events {file}` lists them",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)
        _emit_df(events_[name], limit=limit, as_json=as_json)
        return
    if summary:
        counts = events_.counts
        table = pl.DataFrame({"event": list(counts), "count": list(counts.values())}).sort(
            ["count", "event"], descending=[True, False]
        )
        _emit_df(table, limit=limit, as_json=as_json)
        return
    if as_json:
        typer.echo(json.dumps(events_.names))
    else:
        for event_name in events_.names:
            typer.echo(event_name)


# (command, Demo attribute, help) for commands that print one dataset.
_DATASET_COMMANDS = [
    ("rounds", "rounds", "Print CS2 round timings, winners, and end reasons."),
    ("kills", "kills", "Print CS2 kills with resolved participants."),
    ("damage", "damages", "Print CS2 damage events with resolved participants."),
    ("bomb", "bomb", "Print CS2 bomb actions and sites."),
    ("shots", "shots", "Print CS2 shots with player and weapon state."),
    ("grenades", "grenades", "Print thrown CS2 grenade trajectories."),
    ("fires", "fires", "Print CS2 fire intervals."),
    ("smokes", "smokes", "Print CS2 smoke intervals."),
    ("blinds", "blinds", "Print CS2 flash victims, throwers, and durations."),
    ("item-events", "item_events", "Print CS2 item purchases, pickups, and drops."),
]


def _dataset_command(attribute: str, doc: str) -> Callable[..., None]:
    """Build a command that prints one ``Demo`` dataset."""

    def command(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
        _emit_df(getattr(_load(file), attribute), limit=limit, as_json=as_json)

    command.__doc__ = doc
    return command


for _name, _attribute, _doc in _DATASET_COMMANDS:
    app.command(name=_name, rich_help_panel=_DEMO_PANEL)(_dataset_command(_attribute, _doc))


@app.command(rich_help_panel=_DEMO_PANEL)
def stats(file: DemoArg, as_json: JsonOpt = False) -> None:
    """Print CS2 player statistics."""
    _emit_df(_load(file).stats, as_json=as_json)


# --- map-data cache ------------------------------------------------------------


@app.command(rich_help_panel=_DATA_PANEL)
def get(
    release: ReleaseArg = None,
    force: Annotated[
        bool, typer.Option("--force", help="Re-download even if already cached.")
    ] = False,
) -> None:
    """Download an awpy-data release."""
    path = data.update(release, force=force)
    maps_list = json.loads((path / "manifest.json").read_text()).get("maps", [])
    typer.echo(f"{data.DATA_REPO} {path.name}: {len(maps_list)} maps in {path}")


@app.command(rich_help_panel=_DATA_PANEL)
def versions() -> None:
    """List cached awpy-data versions and check for an update."""
    local = data.local_versions()
    try:
        latest = data.latest_version()
    except Exception:  # offline — still useful to list the cache
        latest = None
    for v in local:
        flags = (("newest local", v == local[-1]), ("latest release", v == latest))
        notes = [note for note, on in flags if on]
        typer.echo(v + (f"  ({', '.join(notes)})" if notes else ""))
    if not local:
        typer.echo("no releases cached" + (f"; the latest is {latest}" if latest else ""))
    if latest and latest not in local:
        typer.echo(f"latest release is {latest} — run `awpy get` to download it")


@app.command(rich_help_panel=_DATA_PANEL)
def maps(release: ReleaseArg = None) -> None:
    """List maps in an awpy-data release."""
    for map_name in data.available_maps(release):
        typer.echo(map_name)


@app.command(rich_help_panel=_DATA_PANEL)
def clear(
    release: ReleaseArg = None,
    delete_all: Annotated[bool, typer.Option("--all", help="Delete the whole cache.")] = False,
) -> None:
    """Delete one awpy-data release or the complete cache."""
    if release is None and not delete_all:
        raise typer.BadParameter("specify a release to clear, or --all for the whole cache")
    data.clear(None if delete_all else release)
    typer.echo("cleared the whole cache" if delete_all else f"cleared {release}")


def main() -> None:
    """Run the Awpy console application."""
    app()


if __name__ == "__main__":
    main()
