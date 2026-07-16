"""``awpy`` — the Awpy command line: inspect CS2 demos and manage map assets.

Demo inspection (thin wrappers over :class:`awpy.Demo`; add ``--json`` for
machine-readable output, ``--limit N`` to cap row-level tables)::

    awpy info match.dem
    awpy rounds match.dem
    awpy kills match.dem --limit 20
    awpy events match.dem --summary
    awpy stats match.dem

Map-data cache management (see :mod:`awpy.data`)::

    awpy get             # download the latest awpy-data release
    awpy get 2000873     # ... or a specific one
    awpy versions        # cached releases, and whether a newer one exists
    awpy maps            # maps available in a release
    awpy clear 2000873   # delete one cached release (--all for everything)

Also runnable as ``python -m awpy``. Parser-internals commands (demo message
stream, entity snapshots, send-tables, string tables) live in the Rust
developer binary ``awpy-dev`` (``cargo install --path crates/awpy-dev``).
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
    """Awpy — parse CS2 demos and manage map-data assets from the command line."""


def _load(file: Path) -> Demo:
    try:
        return Demo(file)
    except InvalidDemoError as exc:
        typer.secho(f"invalid demo file: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _emit_df(df: pl.DataFrame, *, limit: int | None = None, as_json: bool = False) -> None:
    """Print a DataFrame as JSON rows or a full-width terminal table."""
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
    """Check that a file parses as a valid CS2 demo (magic bytes + header)."""
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
    """Print the demo file header and playback info."""
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
    """List the demo's event names, dump one event, or show counts (--summary)."""
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
    """Per-round table: start/freeze-end/end ticks, winner, and end reason."""
    _emit_df(_load(file).rounds, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def kills(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """List kills (from player_death events) with all fields."""
    _emit_df(_load(file).kills, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def damage(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """List damage instances (from player_hurt events) with all fields."""
    _emit_df(_load(file).damages, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def bomb(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """List bomb actions (pickup / drop / plant / defuse) with site."""
    _emit_df(_load(file).bomb, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def shots(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """List shots fired (from weapon_fire events) with shooter/weapon state."""
    _emit_df(_load(file).shots, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def grenades(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Summarize thrown-grenade trajectories."""
    _emit_df(_load(file).grenades, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def fires(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Summarize burning infernos (molotov / incendiary areas)."""
    _emit_df(_load(file).fires, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def smokes(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """Summarize deployed smoke clouds."""
    _emit_df(_load(file).smokes, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def blinds(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """List flash events: who was blinded, by whom, and for how long."""
    _emit_df(_load(file).blinds, limit=limit, as_json=as_json)


@app.command(name="item-events", rich_help_panel=_DEMO_PANEL)
def item_events(file: DemoArg, limit: LimitOpt = None, as_json: JsonOpt = False) -> None:
    """List weapon-item transactions: purchases, pickups, and drops."""
    _emit_df(_load(file).item_events, limit=limit, as_json=as_json)


@app.command(rich_help_panel=_DEMO_PANEL)
def stats(file: DemoArg, as_json: JsonOpt = False) -> None:
    """Per-player scoreboard: kills, KAST, ADR, openings, trades, and more."""
    _emit_df(_load(file).stats, as_json=as_json)


# --- map-data cache ------------------------------------------------------------


@app.command(rich_help_panel=_DATA_PANEL)
def get(
    release: ReleaseArg = None,
    force: Annotated[
        bool, typer.Option("--force", help="Re-download even if already cached.")
    ] = False,
) -> None:
    """Download a release of the awpy-data map assets (default: the latest)."""
    path = data.update(release, force=force)
    maps_list = json.loads((path / "manifest.json").read_text()).get("maps", [])
    typer.echo(f"{data.DATA_REPO} {path.name}: {len(maps_list)} maps in {path}")


@app.command(rich_help_panel=_DATA_PANEL)
def versions() -> None:
    """List cached awpy-data releases, and whether a newer one exists."""
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
    """List maps available in an awpy-data release (default: newest cached)."""
    for map_name in data.available_maps(release):
        typer.echo(map_name)


@app.command(rich_help_panel=_DATA_PANEL)
def clear(
    release: ReleaseArg = None,
    delete_all: Annotated[bool, typer.Option("--all", help="Delete the whole cache.")] = False,
) -> None:
    """Delete one cached awpy-data release, or the whole cache with --all."""
    if release is None and not delete_all:
        raise typer.BadParameter("specify a release to clear, or --all for the whole cache")
    data.clear(None if delete_all else release)
    typer.echo("cleared the whole cache" if delete_all else f"cleared {release}")


def main() -> None:
    """Entry point for the ``awpy`` console script."""
    app()


if __name__ == "__main__":
    main()
