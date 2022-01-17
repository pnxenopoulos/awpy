# CSGO Python Library Visualization
[Index](README.md) | [Data](data.md) | [Demofiles](demofiles.md) | [Parser](parser.md) | [Demo Cleaning](demo_cleaning.md) | [Analytics](analytics.md) | [Visualization](visualization.md)

###### Table of Contents

[Transforming Coordinates](#transforming-coordinates)

[Displaying the Map](#map-display)

[Animated Trajectories](#animated-trajectories)

[Nade Maps](#nade-maps)

##### Transforming Coordinates
In order to plot the CSGO data correctly, we need to transform the coordinates into the correct scales. The `position_transform_x` and `position_transform_y` functions perform this transformation. To use these functions, you just pass in `position_transform_x(map_name, value)`, and the function will return a float. The data used to make the transformation is provided by the game itself, and available in `csgo/data/map/map_data.json`, or via `from csgo import MAP_DATA`.

##### Map Display
The core function of the visualization module is `plot_map`. It takes three arguments: `map_name`, `map_type` and `dark`. The map name is a string that refers to what map you want to plot. The map type is either a string named `"original"` or `"simpleradar"`. The SimpleRadar plots were graciously provided by their team, and contain sharper colors than the original maps. The `dark` parameters is a boolean that is used when `map_type="simpleradar"` is set. Dark will indicate whether or not to use the light or dark theme. The `plot_map` function returns a matplotlib figure and axes, so you would use it like `fig, ax = plot_map(...)`. Then, you can plot whatever you wish.

##### Animated Trajectories
One may want to plot animated trajectories for a round. That's why we provide `plot_round(filename, frames, map_name, map_type, dark)`. The last three parameters are the same as above, but the first, `filename`, is a string, like `"best_round_ever.gif"`. `frames` is a list of frames provided by the parser output. You can just directly pass the round's frames, like `plot_round(..., frames=d['gameRound'][7]['frames'], ...)`, where `d` is the object that holds your parsed data. This function can take a while to run depending on your parse rate, since it creates and temporarily saves an image for each frame passed through. 

##### Nade Maps
Grenade maps are very common. So, we have the function `plot_nades(rounds, nades, side, map_name, map_type, dark)`. As before, the last three parameters are the standard mapping parameters. `rounds` is just a list of rounds, which you can pass by doing something like `d['gameRounds'][i:j]`. `nades` is a list of nades to throw, and the currently supported grenades are `["Flashbang", "HE Grenade", "Smoke Grenade", "Molotov", "Incendiary Grenade"]`. `side` is a string that indicates which side's nades you want to plot.