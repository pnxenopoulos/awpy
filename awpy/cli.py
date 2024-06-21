"""Command-line interface for Awpy."""

from pathlib import Path
from typing import Literal

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
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose mode.")
@click.option("--noticks", is_flag=True, default=False, help="Disable tick parsing.")
@click.option(
    "--rounds",
    is_flag=True,
    default=True,
    help="Get round information for every event.",
)
def parse(
    demo: Path, *, verbose: bool = False, noticks: bool = False, rounds: bool = True
) -> None:
    """Parse a file given its path."""
    demo_path = Path(demo)  # Pathify
    demo = Demo(path=demo_path, verbose=verbose, ticks=not noticks, rounds=rounds)
    demo.compress()
