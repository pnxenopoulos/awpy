"""Defines the DemoHeader dictionary that scores."""

from pydantic import BaseModel


class DemoHeader(BaseModel):
    """Class to store demo header information."""

    demo_version_guid: str
    network_protocol: str
    fullpackets_version: str
    allow_clientside_particles: bool
    addons: str
    client_name: str
    map_name: str
    server_name: str
    demo_version_name: str
    allow_clientside_entities: bool
    demo_file_stamp: str
    game_directory: str
