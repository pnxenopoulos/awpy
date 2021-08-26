def generate_game_state(frame, state_type="vector"):
    """Returns flashes as either a list or Pandas dataframe

    Args:
        frame (dict)        : Dict output of a frame generated from the DemoParser class
        state_type (string) : One of "vector", "graph" or "set"
        split_sides (bool)  : False to return a global state, true to return two states subset by side

    Returns:
        A dict with keys "T", "CT" and "Global"
    """
    if type(frame) is not dict:
        raise ValueError("Frame input must be a dict from the DemoParser.parse() output")
        
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