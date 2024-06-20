"""Command-line interface for Awpy."""

import json
import os
import tempfile
import zipfile
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
            logger.info(f"Getting USD for {resource_name}...")


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
    zip_name = demo_path.stem + ".zip"

    with (
        tempfile.TemporaryDirectory() as tmpdirname,
        zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf,
    ):
        # Get the main dataframes
        for df_name, df in [
            ("kills", demo.kills),
            ("damages", demo.damages),
            ("bomb", demo.bomb),
            ("smokes", demo.smokes),
            ("infernos", demo.infernos),
            ("weapon_fires", demo.weapon_fires),
            ("rounds", demo.rounds),
            ("grenades", demo.grenades),
        ]:
            df_filename = os.path.join(tmpdirname, f"{df_name}.data")
            df.to_parquet(df_filename, index=False)
            zipf.write(df_filename, f"{df_name}.data")

        # Write all events
        for event_name, event in demo.events.items():
            event_filename = os.path.join(tmpdirname, f"{event_name}-event.data")
            event.to_parquet(event_filename, index=False)
            zipf.write(event_filename, os.path.join("events", f"{event_name}.data"))

        # Write ticks
        if not noticks:
            ticks_filename = os.path.join(tmpdirname, "ticks.data")
            demo.ticks.to_parquet(ticks_filename, index=False)
            zipf.write(ticks_filename, "ticks.data")

        header_filename = os.path.join(tmpdirname, "header.json")
        with open(header_filename, "w", encoding="utf-8") as f:
            json.dump(demo.header, f)
        zipf.write(header_filename, "header.json")

        if verbose:
            logger.success(f"Zipped dataframes for {zip_name}")
