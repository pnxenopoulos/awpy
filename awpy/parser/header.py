"""Parsing methods for the header of a Counter-Strike demo file."""

from awpy.parser.models import DemoHeader


def parse_header(parsed_header: dict) -> DemoHeader:
    """Parse the header of the demofile.

    Args:
        parsed_header (dict): The header of the demofile.

    Returns:
        DemoHeader: The parsed header of the demofile.
    """
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
        else:
            pass  # Loop through and convert strings to bools
    return DemoHeader(**parsed_header)
