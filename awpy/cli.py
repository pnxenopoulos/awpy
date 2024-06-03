"""Command-line interface for Awpy."""

import json
import os
import tempfile
import zipfile
from pathlib import Path

import click
from loguru import logger

from awpy import Demo


@click.group()
def awpy() -> None:
    """A simple CLI interface for Awpy."""


@awpy.command(help="Parse a Counter-Strike 2 demo file.")
@click.argument("demo", type=click.Path(exists=True))
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose mode.")
def parse(demo: Path, *, verbose: bool = True) -> None:
    """Parse a file given its path."""
    demo_path = Path(demo)  # Pathify
    demo = Demo(path=demo_path, verbose=verbose)
    zip_name = demo_path.stem + ".zip"

    with (
        tempfile.TemporaryDirectory() as tmpdirname,
        zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf,
    ):
        for df_name, df in [
            ("kills", demo.kills),
            ("damages", demo.damages),
            ("bomb", demo.bomb),
            ("smokes", demo.smokes),
            ("infernos", demo.infernos),
            ("weapon_fires", demo.weapon_fires),
            ("rounds", demo.rounds),
            ("grenades", demo.grenades),
            ("ticks", demo.ticks),
        ]:
            df_filename = os.path.join(tmpdirname, f"{df_name}.data")
            df.to_parquet(df_filename, index=False)
            zipf.write(df_filename, f"{df_name}")

        with open(os.path.join(tmpdirname, "header.json"), "w") as f:
            json.dump(demo.header, f)

        if verbose:
            logger.success(f"Zipped dataframes for {zip_name}")
