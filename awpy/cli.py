"""Command-line interface for Awpy."""

import zipfile
from pathlib import Path
from typing import Literal

import click
import requests
from loguru import logger
from tqdm import tqdm

from awpy import Demo, Nav, Spawns
from awpy.data import AWPY_DATA_DIR, TRI_URL
from awpy.visibility import VphysParser


@click.group()
def awpy() -> None:
    """A simple CLI interface for Awpy."""


@awpy.command(
    name="get",
    help="""
    Get Counter-Strike 2 resources like parsed nav meshes, spawns or triangle files. \n
    Available choices: 'tri', 'map', 'nav', 'spawn'""",
)
@click.argument("resource_type", type=click.Choice(["tri", "nav", "spawn"]))
def get(resource_type: Literal["tri"]) -> None:
    """Get a resource given its type and name."""
    if not AWPY_DATA_DIR.exists():
        AWPY_DATA_DIR.mkdir(parents=True, exist_ok=True)
        awpy_data_dir_creation_msg = f"Created awpy data directory at {AWPY_DATA_DIR}"
        logger.debug(awpy_data_dir_creation_msg)

    if resource_type == "tri":
        tri_data_dir = AWPY_DATA_DIR / "tri"
        tri_data_dir.mkdir(parents=True, exist_ok=True)
        tri_file_path = tri_data_dir / "tris.zip"
        response = requests.get(TRI_URL, stream=True, timeout=300)
        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024
        with (
            tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar,
            open(tri_file_path, "wb") as file,
        ):
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)

        # Unzip the file
        try:
            with zipfile.ZipFile(tri_file_path, "r") as zip_ref:
                zip_ref.extractall(tri_data_dir)
            logger.info(f"Extracted contents of {tri_file_path} to {tri_data_dir}")
        except zipfile.BadZipFile as e:
            logger.error(f"Failed to unzip {tri_file_path}: {e}")
            return

        # Delete the zip file
        tri_file_path.unlink()
        logger.info(f"Deleted the compressed tris {tri_file_path}")
    elif resource_type == "spawn":
        spawn_not_impl_msg = "Spawn files are not yet implemented."
        raise NotImplementedError(spawn_not_impl_msg)
    elif resource_type == "nav":
        nav_not_impl_msg = "Nav files are not yet implemented."
        raise NotImplementedError(nav_not_impl_msg)


@awpy.command(name="parse", help="Parse a Counter-Strike 2 demo (.dem) file .")
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


@awpy.command(name="spawn", help="Parse spawns from a Counter-Strike 2 .vent file.")
@click.argument("vent_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
def parse_spawns(vent_file: Path, *, outpath: Path | None = None) -> None:
    """Parse a nav file given its path."""
    vent_file = Path(vent_file)
    if not outpath:
        output_path = vent_file.with_suffix(".json")
    spawns_data = Spawns.from_vents_file(vent_file)
    spawns_data.to_json(path=output_path)
    logger.success(f"Spawns file saved to {vent_file.with_suffix('.json')}, {spawns_data}")


@awpy.command(name="nav", help="Parse a Counter-Strike 2 .nav file.")
@click.argument("nav_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
def parse_nav(nav_file: Path, *, outpath: Path | None = None) -> None:
    """Parse a nav file given its path."""
    nav_file = Path(nav_file)
    nav_mesh = Nav(path=nav_file)
    if not outpath:
        output_path = nav_file.with_suffix(".json")
    nav_mesh.to_json(path=output_path)
    logger.success(f"Nav mesh saved to {nav_file.with_suffix('.json')}, {nav_mesh}")


@awpy.command(name="tri", help="Parse triangles (*.tri) from a .vphys file.")
@click.argument("vphys_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
def generate_tri(vphys_file: Path, *, outpath: Path | None = None) -> None:
    """Parse a .vphys file into a .tri file."""
    vphys_file = Path(vphys_file)
    vphys_parser = VphysParser(vphys_file)
    vphys_parser.to_tri(path=outpath)
