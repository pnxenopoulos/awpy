"""Command-line interface for Awpy."""

import zipfile
from pathlib import Path
from typing import Literal, Optional

import click
import requests
from loguru import logger
from tqdm import tqdm

from awpy import Demo, Nav, Spawns
from awpy.data import AWPY_DATA_DIR, TRI_URL
from awpy.vis import VphysParser


@click.group()
def awpy() -> None:
    """A simple CLI interface for Awpy."""


@awpy.command(
    help="Get Counter-Strike 2 resources like map images, nav meshes or usd files."
)
@click.argument("resource_type", type=click.Choice(["tri"]))
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
    elif resource_type == "map":
        map_not_impl_msg = "Map files are not yet implemented."
        raise NotImplementedError(map_not_impl_msg)
    elif resource_type == "nav":
        nav_not_impl_msg = "Nav files are not yet implemented."
        raise NotImplementedError(nav_not_impl_msg)


@awpy.command(help="Parse a Counter-Strike 2 demo (.dem) file .")
@click.argument("demo", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose mode.")
@click.option("--noticks", is_flag=True, default=False, help="Disable tick parsing.")
@click.option(
    "--norounds",
    is_flag=True,
    default=False,
    help="Get round information for every event.",
)
@click.option(
    "--player-props", multiple=True, help="List of player properties to include."
)
@click.option(
    "--other-props", multiple=True, help="List of other properties to include."
)
def parse_demo(
    demo: Path,
    *,
    outpath: Optional[Path] = None,
    verbose: bool = False,
    noticks: bool = False,
    norounds: bool = True,
    player_props: Optional[tuple[str]] = None,
    other_props: Optional[tuple[str]] = None,
) -> None:
    """Parse a file given its path."""
    demo_path = Path(demo)  # Pathify
    demo = Demo(
        path=demo_path,
        verbose=verbose,
        ticks=not noticks,
        rounds=not norounds,
        player_props=player_props[0].split(",") if player_props else None,
        other_props=other_props[0].split(",") if other_props else None,
    )
    demo.compress(outpath=outpath)


@awpy.command(help="Parse spawns from a Counter-Strike 2 .vent file.")
@click.argument("vent_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
def parse_spawns(vent_file: Path, *, outpath: Optional[Path] = None) -> None:
    """Parse a nav file given its path."""
    vent_file = Path(vent_file)
    if not outpath:
        output_path = vent_file.with_suffix(".json")
    spawns_data = Spawns.from_vents_file(vent_file)
    spawns_data.to_json(path=output_path)
    logger.success(
        f"Spawns file saved to {vent_file.with_suffix('.json')}, {spawns_data}"
    )


@awpy.command(help="Parse a Counter-Strike 2 nav (.nav) file.")
@click.argument("nav_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
def parse_nav(nav_file: Path, *, outpath: Optional[Path] = None) -> None:
    """Parse a nav file given its path."""
    nav_file = Path(nav_file)
    nav_mesh = Nav(path=nav_file)
    if not outpath:
        output_path = nav_file.with_suffix(".json")
    nav_mesh.to_json(path=output_path)
    logger.success(f"Nav mesh saved to {nav_file.with_suffix('.json')}, {nav_mesh}")


@awpy.command(help="Parse triangles (*.tri) from a .vphys file.")
@click.argument("vphys_file", type=click.Path(exists=True))
@click.option("--outpath", type=click.Path(), help="Path to save the compressed demo.")
def generate_tri(vphys_file: Path, *, outpath: Optional[Path] = None) -> None:
    """Parse a .vphys file into a .tri file."""
    vphys_file = Path(vphys_file)
    vphys_parser = VphysParser(vphys_file)
    vphys_parser.to_tri(path=outpath)
