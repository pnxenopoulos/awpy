"""Command-line interface for Awpy."""

from pathlib import Path
from typing import Literal

import click
from loguru import logger

import awpy.data
import awpy.data.map_data
import awpy.data.utils
from awpy import Demo, Nav, Spawns
from awpy.visibility import VphysParser


@click.group(name="awpy")
def awpy_cli() -> None:
    """A simple CLI interface for Awpy."""


@awpy_cli.command(
    name="get",
    help=f"""
    Get Counter-Strike 2 resources like parsed map data or nav meshes. Available choices: {awpy.data.POSSIBLE_ARTIFACTS}""",  # noqa: E501
)
@click.argument("resource_type", type=click.Choice(awpy.data.POSSIBLE_ARTIFACTS))
@click.option("--patch", type=int, help="Patch number to fetch the resources.", default=awpy.data.CURRENT_BUILD_ID)
def get(resource_type: Literal["maps", "navs", "tris"], *, patch: int = awpy.data.CURRENT_BUILD_ID) -> None:
    """Get a resource given its type and name."""
    awpy.data.utils.create_data_dir_if_not_exists()

    if resource_type in awpy.data.POSSIBLE_ARTIFACTS:
        awpy.data.utils.fetch_resource(resource_type, patch)
    else:
        resource_not_impl_err_msg = f"Resource type {resource_type} is not yet implemented."
        raise NotImplementedError(resource_not_impl_err_msg)


@awpy_cli.command(name="artifacts", help="Information on Awpy artifacts.")
def artifacts() -> None:
    """Print information on Awpy artifacts."""
    print("Current patch:", awpy.data.CURRENT_BUILD_ID)
    for patch, patch_data in awpy.data.AVAILABLE_PATCHES.items():
        print(
            f"Patch {patch} ({patch_data['datetime']}, {patch_data['url']}). Available artifacts: {patch_data['available']}\n"  # noqa: E501
        )


@awpy_cli.command(name="parse", help="Parse a Counter-Strike 2 demo (.dem) file.")
@click.argument("demo_path", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
@click.option("--events", multiple=True, help="List of events to parse.")
@click.option("--player-props", multiple=True, help="List of player properties to include.")
@click.option("--other-props", multiple=True, help="List of other properties to include.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose mode.")
def parse_demo(
    demo_path: Path,
    *,
    outpath: Path | None = None,
    events: tuple[str] | None = None,
    player_props: tuple[str] | None = None,
    other_props: tuple[str] | None = None,
    verbose: bool = False,
) -> None:
    """Parse a file given its path."""
    demo_path = Path(demo_path)  # Pathify
    demo = Demo(path=demo_path, verbose=verbose)
    demo.parse(
        events=events[0].split(",") if events else None,
        player_props=player_props[0].split(",") if player_props else None,
        other_props=other_props[0].split(",") if other_props else None,
    )
    demo.compress(outpath=outpath)


@awpy_cli.command(name="spawn", help="Parse spawns from a Counter-Strike 2 .vent file.", hidden=True)
@click.argument("vent_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the spawns.")
def parse_spawn(vent_file: Path, *, outpath: Path | None = None) -> None:
    """Parse a nav file given its path."""
    vent_file = Path(vent_file)
    if not outpath:
        outpath = vent_file.with_suffix(".json")
    spawns_data = Spawns.from_vents_file(vent_file)
    spawns_data.to_json(path=outpath)
    logger.success(f"Spawns file saved to {vent_file.with_suffix('.json')}, {spawns_data}")


@awpy_cli.command(name="nav", help="Parse a Counter-Strike 2 .nav file.", hidden=True)
@click.argument("nav_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the nav file.")
def parse_nav(nav_file: Path, *, outpath: Path | None = None) -> None:
    """Parse a nav file given its path."""
    nav_file = Path(nav_file)
    nav_mesh = Nav.from_path(path=nav_file)
    if not outpath:
        outpath = nav_file.with_suffix(".json")
    nav_mesh.to_json(path=outpath)
    logger.success(f"Nav mesh saved to {nav_file.with_suffix('.json')}, {nav_mesh}")


@awpy_cli.command(name="mapdata", help="Parse Counter-Strike 2 map images.", hidden=True)
@click.argument("overview_dir", type=click.Path(exists=True))
def parse_mapdata(overview_dir: Path) -> None:
    """Parse radar overview images given an overview."""
    overview_dir = Path(overview_dir)
    if not overview_dir.is_dir():
        overview_dir_err_msg = f"{overview_dir} is not a directory."
        raise NotADirectoryError(overview_dir_err_msg)
    map_data = awpy.data.map_data.map_data_from_vdf_files(overview_dir)
    awpy.data.map_data.update_map_data_file(map_data, "map-data.json")
    logger.success("Map data saved to map_data.json")


@awpy_cli.command(name="tri", help="Parse triangles (*.tri) from a .vphys file.", hidden=True)
@click.argument("vphys_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the parsed triangle.")
def generate_tri(vphys_file: Path, *, outpath: Path | None = None) -> None:
    """Parse a .vphys file into a .tri file."""
    vphys_file = Path(vphys_file)
    vphys_parser = VphysParser(vphys_file)
    vphys_parser.to_tri(path=outpath)
    logger.success(f"Tri file saved to {outpath}")
