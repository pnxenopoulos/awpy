import numpy as np

from csgo.analytics.distance import area_distance, point_distance


def frame_to_graph(frame, metric, map_name, full=False):
    """Transforms a frame to a graph

    Args:
        frame (dictionary) : A frame from the dict in csgo.parser.DemoParser
        metric (string)    : A string indicating "graph" for graph distance or one of 'euclidean', 'manhattan', 'canberra', 'cosine'
        map_name (string)  : A string indicating the map
        full (boolean)     : True for full graphs (force 10 nodes) or False for graph of only alive players

        Returns:
            A (np.array) : Adjacency matrix using graph distances
            X (np.array) : Matrix with information on each node
    """
    if map_name not in [
        "de_dust2",
        "de_cbble",
        "de_inferno",
        "de_mirage",
        "de_nuke",
        "de_overpass",
        "de_train",
        "de_vertigo",
    ]:
        raise ValueError(
            f'Invalid map name: got {map}, expected one of: "de_dust2", "de_cbble", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train", "de_vertigo"'
        )
    if frame["T"]["Players"] is None or frame["CT"]["Players"] is None:
        raise ValueError("No players!")
    players = frame["T"]["Players"] + frame["CT"]["Players"]
    # Create player nodes
    nodes = []
    if len(frame["T"]["Players"]) > 0:
        for p in frame["T"]["Players"]:
            side_ind = 0
            if full:
                nodes.append(
                    [
                        side_ind,
                        p["IsAlive"],
                        p["Hp"],
                        p["Armor"],
                        p["EquipmentValue"],
                        p["HasHelmet"],
                        p["HasDefuse"],
                        p["TotalUtility"],
                        p["DistToBombsiteA"],
                        p["DistToBombsiteB"],
                    ]
                )
            elif full is False and p["IsAlive"] is True:
                nodes.append(
                    [
                        side_ind,
                        p["Hp"],
                        p["Armor"],
                        p["EquipmentValue"],
                        p["HasHelmet"],
                        p["HasDefuse"],
                        p["TotalUtility"],
                        p["DistToBombsiteA"],
                        p["DistToBombsiteB"],
                    ]
                )
    if len(frame["CT"]["Players"]) > 0:
        for p in frame["CT"]["Players"]:
            side_ind = 1
            if full:
                nodes.append(
                    [
                        side_ind,
                        p["IsAlive"],
                        p["Hp"],
                        p["Armor"],
                        p["EquipmentValue"],
                        p["HasHelmet"],
                        p["HasDefuse"],
                        p["TotalUtility"],
                        p["DistToBombsiteA"],
                        p["DistToBombsiteB"],
                    ]
                )
            elif full is False and p["IsAlive"] is True:
                nodes.append(
                    [
                        side_ind,
                        p["Hp"],
                        p["Armor"],
                        p["EquipmentValue"],
                        p["HasHelmet"],
                        p["HasDefuse"],
                        p["TotalUtility"],
                        p["DistToBombsiteA"],
                        p["DistToBombsiteB"],
                    ]
                )
    # Create adjacency matrix
    adjacency = []
    for p1 in players:
        player_distances = []
        if full:
            for p2 in players:
                if metric == "graph":
                    player_distances.append(
                        area_distance(
                            area_one=p1["AreaId"], area_two=p2["AreaId"], map=map_name
                        )
                    )
                else:
                    player_distances.append(
                        point_distance(
                            point_a=[p1["X"], p1["Y"], p1["Z"]],
                            point_b=[p2["X"], p2["Y"], p2["Z"]],
                            type=metric,
                            map=map_name,
                        )
                    )
                adjacency.append(player_distances)
        else:
            if p1["IsAlive"]:
                for p2 in players:
                    if p2["IsAlive"]:
                        if metric == "graph":
                            player_distances.append(
                                area_distance(
                                    area_one=p1["AreaId"], area_two=p2["AreaId"], map=map_name
                                )
                            )
                        else:
                            player_distances.append(
                                point_distance(
                                    point_a=[p1["X"], p1["Y"], p1["Z"]],
                                    point_b=[p2["X"], p2["Y"], p2["Z"]],
                                    type=metric,
                                    map=map_name,
                                )
                            )
                        adjacency.append(player_distances)
    X = np.array(nodes)
    A = np.array(adjacency)
    return X, A
