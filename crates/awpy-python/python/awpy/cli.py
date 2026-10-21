"""Inspect demos and manage map assets with ``awpy`` or ``python -m awpy``.

Use ``awpy --help`` for commands. The separate Rust binary ``awpy-dev``
provides parser-internal inspection.
"""

import json
import shutil
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
    """Print the Awpy version when requested.

    Args:
        value: Whether the eager version option was selected.
    """
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
    """Parse CS2 demos and manage map assets with the Awpy CLI.

    Args:
        version: Show the package version and exit.
    """


def _load(file: Path) -> Demo:
    """Open a CS2 demo for CLI inspection.

    Args:
        file: Path to a CS2 demo.

    Returns:
        The opened ``Demo``.
    """
    try:
        return Demo(file)
    except InvalidDemoError as exc:
        typer.secho(f"invalid demo file: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _emit_df(df: pl.DataFrame, *, limit: int | None = None, as_json: bool = False) -> None:
    """Print Polars rows as JSON or a terminal table.

    Args:
        df: Polars DataFrame to print.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
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
    """Check the CS2 demo header and file signature.

    Args:
        file: Path to a CS2 demo.
        as_json: Write JSON rows instead of a terminal table.
    """
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
    """Print CS2 demo header and playback metadata.

    Args:
        file: Path to a CS2 demo.
        as_json: Write JSON rows instead of a terminal table.
    """
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
    """List CS2 game events, counts, or rows for one event.

    Args:
        file: Path to a CS2 demo.
        name: Game-event name, or ``None`` to list names.
        summary: Print event counts instead of event rows.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
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


@app.command(rich_help_panel=_DEMO_PANEL)
def rounds(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 round timings, winners, and end reasons.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).rounds, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def kills(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 kills with resolved participants.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).kills, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def damage(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 damage events with resolved participants.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).damages, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def bomb(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 bomb actions and sites.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).bomb, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def shots(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 shots with player and weapon state.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).shots, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def grenades(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print thrown CS2 grenade trajectories.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).grenades, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def fires(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 fire intervals.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).fires, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def smokes(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 smoke intervals.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).smokes, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def blinds(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 flash victims, throwers, and durations.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).blinds, limit=limit, as_json=as_json)


@app.command(name="item-events", rich_help_panel=_DEMO_PANEL)
def item_events(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Print CS2 item purchases, pickups, and drops.

    Args:
        file: Path to a CS2 demo.
        limit: Maximum output rows, or ``None`` for all rows.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).item_events, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def stats(file: DemoArg, as_json: JsonOpt = False) -> None:
    """Print CS2 player statistics.

    Args:
        file: Path to a CS2 demo.
        as_json: Write JSON rows instead of a terminal table.
    """
    _emit_df(_load(file).stats, as_json=as_json)


# --- map-data cache ------------------------------------------------------------


@app.command(rich_help_panel=_DATA_PANEL)
def get(
    release: ReleaseArg = None,
    force: Annotated[
        bool, typer.Option("--force", help="Re-download even if already cached.")
    ] = False,
) -> None:
    """Download an awpy-data release.

    Args:
        release: awpy-data ClientVersion, or ``None`` for the command default.
        force: Download the selected release again.
    """
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
    """List maps in an awpy-data release.

    Args:
        release: awpy-data ClientVersion, or ``None`` for the command default.
    """
    for map_name in data.available_maps(release):
        typer.echo(map_name)


@app.command(rich_help_panel=_DATA_PANEL)
def clear(
    release: ReleaseArg = None,
    delete_all: Annotated[bool, typer.Option("--all", help="Delete the whole cache.")] = False,
) -> None:
    """Delete one awpy-data release or the complete cache.

    Args:
        release: awpy-data ClientVersion, or ``None`` for the command default.
        delete_all: Delete the entire cache instead of one release.
    """
    if release is None and not delete_all:
        raise typer.BadParameter("specify a release to clear, or --all for the whole cache")
    data.clear(None if delete_all else release)
    typer.echo("cleared the whole cache" if delete_all else f"cleared {release}")


def main() -> None:
    """Run the Awpy console application."""
    app()


if __name__ == "__main__":
    main()
