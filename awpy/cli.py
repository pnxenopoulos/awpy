"""Command-line interface for Awpy."""

from pathlib import Path
from typing import Literal, Optional

import click
import requests
from loguru import logger
from tqdm import tqdm

from awpy import Demo
from awpy.data import AWPY_DATA_DIR
from awpy.data.usd_data import USD_LINKS


@click.group()
def awpy() -> None:
    """A simple CLI interface for Awpy."""


@awpy.command(
    help="Get Counter-Strike 2 resources like map images, nav meshes or usd files."
)
@click.argument("resource_type", type=click.Choice(["map", "nav", "usd"]))
@click.argument("resource_name", required=False)
def get(
    resource_type: Literal["map", "nav", "usd"], resource_name: Optional[str]
) -> None:
    """Get a resource given its type and name."""
    if not AWPY_DATA_DIR.exists():
        AWPY_DATA_DIR.mkdir(parents=True, exist_ok=True)
        awpy_data_dir_creation_msg = f"Created awpy data directory at {AWPY_DATA_DIR}"
        logger.debug(awpy_data_dir_creation_msg)

    if resource_type == "usd":
        if resource_name:
            url = USD_LINKS.get(resource_name)
            if not url:
                logger.error(f"No USD link found for {resource_name}")
                return
            usd_data_dir = AWPY_DATA_DIR / "usd"
            usd_data_dir.mkdir(parents=True, exist_ok=True)
            usd_file_path = usd_data_dir / f"{resource_name}.usdc"
            logger.info(f"Getting USD for {resource_name}...")
            response = requests.get(url, stream=True, timeout=300)
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024
            with (
                tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar,
                open(usd_file_path, "wb") as file,
            ):
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    file.write(data)
            logger.info(f"Saved USD for {resource_name} to {usd_file_path}")
        else:
            logger.info("Getting all USDs...")
            for map_name, url in USD_LINKS.items():
                usd_data_dir = AWPY_DATA_DIR / "usd"
                usd_data_dir.mkdir(parents=True, exist_ok=True)
                usd_file_path = usd_data_dir / f"{map_name}.usdc"
                logger.info(f"Getting USD for {map_name}...")
                response = requests.get(url, stream=True, timeout=300)
                total_size = int(response.headers.get("content-length", 0))
                block_size = 1024
                with (
                    tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar,
                    open(usd_file_path, "wb") as file,
                ):
                    for data in response.iter_content(block_size):
                        progress_bar.update(len(data))
                        file.write(data)
                logger.info(f"Saved USD for {map_name} to {usd_file_path}")
    elif resource_type == "map":
        map_not_impl_msg = "Map files are not yet implemented."
        raise NotImplementedError(map_not_impl_msg)
    elif resource_type == "nav":
        nav_not_impl_msg = "Nav files are not yet implemented."
        raise NotImplementedError(nav_not_impl_msg)


@awpy.command(help="Parse a Counter-Strike 2 demo file.")
@click.argument("demo_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--outpath",
    type=click.Path(path_type=Path),
    help="Path to save the compressed demo.",
)
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
def parse(
    demo_path: Path,
    *,
    outpath: Optional[Path] = None,
    verbose: bool = False,
    noticks: bool = False,
    norounds: bool = True,
    player_props: Optional[tuple[str]] = None,
    other_props: Optional[tuple[str]] = None,
) -> None:
    """Parse a file given its path."""  # Pathify
    demo = Demo(
        path=demo_path,
        verbose=verbose,
        ticks=not noticks,
        rounds=not norounds,
        player_props=player_props[0].split(",") if player_props else None,
        other_props=other_props[0].split(",") if other_props else None,
    )
    demo.compress(outpath=outpath)
