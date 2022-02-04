Data
===========

This module contains both data, primarily related to maps and navigation meshes. Additionally, if you look in the repository, you can find images of popular maps, which we use for visualization. The relevant imports are

.. code-block:: python

    from awpy.data import NAV, NAV_GRAPHS, NAV_CSV

`NAV` is a dictionary where the top-level keys are map names (strings) and the next-level keys are area ids (integers). The list of acceptable map names is `['de_train', 'de_cache', 'de_ancient', 'de_overpass', 'de_dust2', 'de_cbble', 'de_inferno', 'de_nuke', 'de_vertigo', 'de_mirage']`.

By running `NAV["de_dust2"][1213]`, we would see

.. code-block:: json

    {
        'areaName': 'BombsiteA', 
        'northWestX': 1050.0, 
        'northWestY': 2303.518799, 
        'northWestZ': 128.03125, 
        'southEastX': 1125.0, 
        'southEastY': 2320.481201, 
        'southEastZ': 128.03125
    }

`NAV_GRAPHS` is a dictionary where the top-level keys are map names (strings) and the values are a `networkx` graph.

`NAV_CSV` contains the information that is in `NAV` but in a pandas DataFrame.