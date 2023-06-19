"""Functions to generate game stats based on snapshots from a demofile."""
# pylint: disable=unused-argument
from awpy.types import GameFrame


def generate_vector_state(frame: GameFrame, map_name: str) -> dict:
    """Returns a game state in a dictionary format.

    Args:
        frame (GameFrame) : Dict output of a frame generated from the DemoParser class
        map_name (string): String indicating the map name

    Returns:
        A dict with keys for each feature.
    """
    game_state: dict = {
        "mapName": map_name,
        "secondsSincePhaseStart": frame["seconds"],
        "bombPlanted": frame["bombPlanted"],
        "bombsite": frame["bombsite"],
        "totalSmokes": len(frame["smokes"] or []),
        "totalFires": len(frame["fires"] or []),
        "ctAlive": 0,
        "ctHp": 0,
        "ctArmor": 0,
        "ctHelmet": 0,
        "ctEq": 0,
        "ctUtility": 0,
        "ctEqValStart": 0,
        "ctBombZone": 0,
        "defusers": 0,
        "tAlive": 0,
        "tHp": 0,
        "tArmor": 0,
        "tHelmet": 0,
        "tEq": 0,
        "tUtility": 0,
        "tEqValStart": 0,
        "tHoldingBomb": 0,
        "tBombZone": 0,
    }
    for player in frame["ct"]["players"] or []:
        game_state["ctEqValStart"] += player["equipmentValueFreezetimeEnd"]
        if player["isAlive"]:
            game_state["ctAlive"] += 1
            game_state["ctHp"] += player["hp"]
            game_state["ctArmor"] += player["armor"]
            game_state["ctHelmet"] += player["hasHelmet"]
            game_state["ctEq"] += player["equipmentValue"]
            game_state["ctUtility"] += player["totalUtility"]
            game_state["defusers"] += player["hasDefuse"]
            # This does not seem to work correctly
            # It is never filled in parse_demo.go
            if player["isInBombZone"]:
                game_state["ctBombZone"] += 1
    for player in frame["t"]["players"] or []:
        game_state["tEqValStart"] += player["equipmentValueFreezetimeEnd"]
        if player["isAlive"]:
            game_state["tAlive"] += 1
            game_state["tHp"] += player["hp"]
            game_state["tArmor"] += player["armor"]
            game_state["tHelmet"] += player["hasHelmet"]
            game_state["tEq"] += player["equipmentValue"]
            game_state["tUtility"] += player["totalUtility"]
            # This does not seem to work correctly
            # It is never filled in parse_demo.go
            if player["isInBombZone"]:
                game_state["tBombZone"] += 1
            if player["hasBomb"]:
                game_state["tHoldingBomb"] = 1

    return game_state


def generate_graph_state(frame: GameFrame) -> dict:
    """Returns a game state as a graph.

    Args:
        frame (GameFrame) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global",
        where each entry is a vector. Global vector is CT + T concatenated
    """
    return {"ct": [], "t": [], "global": []}


def generate_set_state(frame: GameFrame) -> dict:
    """Returns a game state as a set.

    Args:
        frame (GameFrame) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global",
        where each entry is a vector. Global vector is CT + T concatenated
    """
    return {"ct": [], "t": [], "global": []}
