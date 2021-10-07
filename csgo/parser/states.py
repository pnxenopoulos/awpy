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
        state = _generate_vector_state(frame)

    if state_type == "graph":
        state = _generate_graph_state(frame)

    if state_type == "set":
        state = _generate_set_state(frame)

    return state


def _generate_team_vector_state(frame_side):
    """Returns a team's game state as a vector.

    Args:
        frame_side (dict) : Dict output of a frame side generated from the DemoParser class

    Returns:
        A list with numeric elements
    """
    eq_val = 0
    players_remaining = 0
    full_hp_players_remaining = 0
    hp_remaining = 0
    armor_remaining = 0
    helmets_remaining = 0
    defuse_kits_remaining = 0
    for player in frame_side["players"]:
        if player["isAlive"]:
            eq_val += player["equipmentValue"]
            players_remaining += 1
            hp_remaining += player["hp"]
            armor_remaining += player["armor"]
            if player["hasHelmet"]:
                helmets_remaining += 1
            if player["hasDefuse"]:
                defuse_kits_remaining += 1
            if player["hp"] == 100:
                full_hp_players_remaining += 1
    return [
        eq_val,
        players_remaining,
        hp_remaining,
        full_hp_players_remaining,
        armor_remaining,
        helmets_remaining,
        defuse_kits_remaining,
    ]


def _generate_world_vector_state(frame):
    """Generate's the world state as a vector

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A list with numeric elements
    """
    bomb_planted = 0
    if frame["bombPlanted"]:
        bomb_planted = 1
    return [
        frame["seconds"],
        bomb_planted,
        frame["bombsite"],
    ]


def _generate_vector_state(frame):
    """Returns a game state as a vector. The vector includes the following information:

    - Second in the round
    - Equipment Value
    - Players Remaining
    - HP Remaining
    - Armor Remaining
    - Bomb Planted/Site
    - Total Utility
    - Helmets
    - Defuse Kits
    - Bombsite Distance

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    state = {}
    state["ct"] = _generate_team_vector_state(frame["ct"])
    state["t"] = _generate_team_vector_state(frame["t"])
    state["global"] = _generate_world_vector_state(frame)
    return state


def _generate_graph_state(frame):
    """Returns a game state as a graph

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    return {"ct": [], "t": [], "global": []}


def _generate_set_state(frame):
    """Returns a game state as a set

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class

    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    return {"ct": [], "t": [], "global": []}
