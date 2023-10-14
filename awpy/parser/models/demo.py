from typing import TypedDict
from .header import DemoHeader
from .game import Round

class Demo(TypedDict):
    """Class to store a demo's data"""
    header: DemoHeader
    rounds: list[Round]