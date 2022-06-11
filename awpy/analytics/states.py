def generate_game_state(frame, state_type="vector"):
    """Returns a frame into a game state form (one of vector, graph or set)

    Args:
        frame (dict)        : Dict output of a frame generated from the DemoParser class
        state_type (string) : One of "vector", "graph" or "set"

    Returns:
        A dict with keys "T", "CT" and "Global" containing the state representation
    """
    if type(frame) is not dict:
        raise ValueError(
            "Frame input must be a dict from the DemoParser.parse() output"
        )

    if state_type not in ["vector", "graph", "set"]:
        raise ValueError("Supported state types are vector, graph and set.")

    state = None

    if state_type == "vector":
        state = generate_vector_state(frame)

    if state_type == "graph":
        state = generate_graph_state(frame)

    if state_type == "set":
        state = generate_set_state(frame)

    return state


def generate_vector_state(frame):
    """Returns a game state in a dictionary format.

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys for each feature.
    """
    game_state = {}
    game_state["secondsSincePhaseStart"] = frame["seconds"]
    game_state["bombPlanted"] = frame["bombPlanted"]
    game_state["bombsite"] = frame["bombsite"]
    game_state["totalSmokes"] = len(frame["smokes"])
    game_state["totalFires"] = len(frame["fires"])

    # Team specific info (CT)
    game_state["ctAlive"] = 0
    game_state["ctHp"] = 0
    game_state["ctArmor"] = 0
    game_state["ctHelmet"] = 0
    game_state["ctEq"] = 0
    game_state["ctUtility"] = 0
    game_state["ctEqValStart"] = 0
    game_state["ctBombZone"] = 0
    game_state["defusers"] = 0
    for p in frame["ct"]["players"]:
        game_state["ctEqValStart"] += p["equipmentValueFreezetimeEnd"]
        if p["isAlive"]:
            game_state["ctAlive"] += 1
            game_state["ctHp"] += p["hp"]
            game_state["ctArmor"] += p["armor"]
            game_state["ctHelmet"] += p["hasHelmet"]
            game_state["ctEq"] += p["equipmentValue"]
            game_state["ctUtility"] += p["totalUtility"]
            game_state["defusers"] += p["hasDefuse"]
            if p["isInBombZone"]:
                game_state["ctBombZone"] += 1

    # Team specific info (T)
    game_state["tAlive"] = 0
    game_state["tHp"] = 0
    game_state["tArmor"] = 0
    game_state["tHelmet"] = 0
    game_state["tEq"] = 0
    game_state["tUtility"] = 0
    game_state["tEqValStart"] = 0
    game_state["tHoldingBomb"] = 0
    game_state["tBombZone"] = 0
    for p in frame["t"]["players"]:
        game_state["tEqValStart"] += p["equipmentValueFreezetimeEnd"]
        if p["isAlive"]:
            game_state["tAlive"] += 1
            game_state["tHp"] += p["hp"]
            game_state["tArmor"] += p["armor"]
            game_state["tHelmet"] += p["hasHelmet"]
            game_state["tEq"] += p["equipmentValue"]
            game_state["tUtility"] += p["totalUtility"]
            if p["isInBombZone"]:
                game_state["tBombZone"] += 1
            if p["hasBomb"]:
                game_state["tHoldingBomb"] = 1

    return game_state


def generate_graph_state(frame):
    """Returns a game state as a graph

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    return {"ct": [], "t": [], "global": []}


def generate_set_state(frame):
    """Returns a game state as a set

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    return {"ct": [], "t": [], "global": []}
