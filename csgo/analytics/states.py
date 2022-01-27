def generate_game_state(frame, mapName, state_type="vector"):
    """Returns a frame into a game state form (one of vector, graph or set)

    Args:
        frame (dict)        : Dict output of a frame generated from the DemoParser class
        state_type (string) : One of "vector", "graph" or "set"
        mapName (string)    : The map of the match

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
        state = generate_vector_state(frame, mapName)

    if state_type == "graph":
        state = generate_graph_state(frame)

    if state_type == "set":
        state = generate_set_state(frame)

    return state


def generate_team_vector_state(frame_side):
    """Returns a team's game state as a vector. The included features are the total players remaining, full hp players remaining, hp, armor,        helmets, equipment value and defuse kits.

    Args:
        frame_side (dict) : Dict output of a frame side generated from the DemoParser class

    Returns:
        A list with numeric elements
    """
    team_state = {}
    team_state["eqVal"] = frame_side["teamEqVal"]
    team_state["playersRemaining"] = frame_side["alivePlayers"]
    team_state["fullHpPlayersRemaining"] = 0
    team_state["hp"] = 0
    team_state["armor"] = 0
    team_state["helmets"] = 0
    team_state["defuseKits"] = 0
    team_state["flashbangs"] = 0
    team_state["heGrenades"] = 0
    team_state["incendiaryGrenades/molotovs"] = 0
    team_state["smokeGrenades"] = 0
    for player in frame_side["players"]:
        if player["isAlive"]:
            team_state["hp"] += player["hp"]
            team_state["armor"] += player["armor"]
            team_state["helmets"] += player["hasHelmet"]
            team_state["defuseKits"] += player["hasDefuse"]
            team_state["fullHpPlayersRemaining"] += player["hp"] == 100
            for weapon in player["inventory"]: 
                if weapon["weaponName"] == "Flashbang":
                    team_state["flashbangs"] += weapon["ammoInMagazine"] + weapon["ammoInReserve"]
                if weapon["weaponName"] == "HE Grenade":
                    team_state["heGrenades"] += weapon["ammoInMagazine"] + weapon["ammoInReserve"]
                if weapon["weaponName"] in ["Incendiary Grenade", "Molotov"]:
                    team_state["incendiaryGrenades/molotovs"] += weapon["ammoInMagazine"] + weapon["ammoInReserve"]
                if weapon["weaponName"] == "Smoke Grenade":
                    team_state["smokeGrenades"] += weapon["ammoInMagazine"] + weapon["ammoInReserve"]   
    return team_state


def generate_world_vector_state(frame, mapName):
    """Generate's the world state as a vector

    Args:
        frame (dict) : Dict output of a frame generated from the DemoParser class
        mapName (string): The map of the match
        
    Returns:
        A list with numeric elements
    """
    world_state = {}
    world_state["map"] = mapName
    world_state["bombPlanted"] = 0
    world_state["bombPlanted"] += frame["bombPlanted"]
    world_state["secondsRemainingInPhase"] = frame["seconds"]
    world_state["bombsite"] = frame["bombsite"]
    return world_state


def generate_vector_state(frame, mapName):
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
        mapName (string): The map of the match
        
    Returns:
        A dict with keys "T", "CT" and "Global", where each entry is a vector. Global vector is CT + T concatenated
    """
    state = {}
    state["ct"] = generate_team_vector_state(frame["ct"])
    state["t"] = generate_team_vector_state(frame["t"])
    state["global"] = generate_world_vector_state(frame, mapName)
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
