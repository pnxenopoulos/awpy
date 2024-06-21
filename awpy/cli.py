"""Command-line interface for Awpy."""

from pathlib import Path
from typing import Literal, Optional

import click
from loguru import logger

from awpy import Demo


@click.group()
def awpy() -> None:
    """A simple CLI interface for Awpy."""


@awpy.command(help="Get Counter-Strike 2 resources like map files.")
@click.argument("resource_type", type=click.Choice(["map", "usd"]))
@click.argument("resource_name", type=str)
def get(resource_type: Literal["usd"], resource_name: str) -> None:
    """Get a resource given its type and name."""
    if resource_type == "usd":
        if resource_name == "all":
            logger.info("Getting all USDs...")
        else:
            getting_specific_usd_msg = f"Getting USD for {resource_name}..."
            logger.info(getting_specific_usd_msg)


@awpy.command(help="Parse a Counter-Strike 2 demo file.")
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
def parse(
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
