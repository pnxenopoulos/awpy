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


def generate_team_vector_state(frame_side):
    """Returns a team's game state as a vector. The included features are the total players remaining, full hp players remaining, hp, armor, helmets, equipment value and defuse kits.

    Args:
        frame_side (dict) : Dict output of a frame side generated from the DemoParser class

    Returns:
        A list with numeric elements
    """
    team_state = {}
    team_state["eqVal"] = 0
    team_state["playersRemaining"] = 0
    team_state["fullHpPlayersRemaining"] = 0
    team_state["hp"] = 0
    team_state["armor"] = 0
    team_state["helmets"] = 0
    team_state["defuseKits"] = 0
    for player in frame_side["players"]:
        if player["isAlive"]:
            team_state["eqVal"] += player["equipmentValue"]
            team_state["playersRemaining"] += 1
            team_state["hp"] += player["hp"]
            team_state["armor"] += player["armor"]
            if player["hasHelmet"]:
                team_state["helmets"] += 1
            if player["hasDefuse"]:
                team_state["defuseKits"] += 1
            if player["hp"] == 100:
                team_state["fullHpPlayersRemaining"] += 1
    return team_state


def generate_world_vector_state(frame):
    """Generate's the world state as a vector

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A list with numeric elements
    """
    world_state = {}
    world_state["bombPlanted"] = 0
    if frame["bombPlanted"]:
        world_state["bombPlanted"] = 1
    world_state["secondsRemainingInPhase"] = frame["seconds"]
    world_state["bombsite"] = frame["bombsite"]
    return world_state


def generate_vector_state(frame):
    """Returns a game state as a vector. The vector includes the following information:

    For each team:
        - players remaining
        - full hp players remaining
        - total hp
        - total armor
        - total helmets
        - total equipment value
        - total defuse kits

    For the world state:
        - seconds since the beginning of the game phase (bomb planted/not)
        - bomb plant
        - bomb site where bomb is planted

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    state = {}
    state["ct"] = generate_team_vector_state(frame["ct"])
    state["t"] = generate_team_vector_state(frame["t"])
    state["global"] = generate_world_vector_state(frame)
    return state


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
