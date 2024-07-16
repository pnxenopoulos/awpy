Data
===========

This module contains both data, primarily related to map (e.g., images, navigation meshes and USD files). For example, you can get basic map information with `MAP_DATA`:

.. code-block:: python

    from awpy.data.map_data import MAP_DATA

`MAP_DATA` is a dictionary where the top-level keys are map names (strings) and the next-level keys are scaling properties for the map. Below, we show an example for one map.

.. code-block:: json

    "ar_baggage": {
        "pos_x": -1316,
        "pos_y": 1288,
        "scale": 2.539062,
        "rotate": 1,
        "zoom": 1.3,
        "selections": [
            {"name": "default", "altitude_max": 10000, "altitude_min": -5},
            {"name": "lower", "altitude_max": -5, "altitude_min": -10000},
        ],
    }