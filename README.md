<div align="center">
<h1>Awpy</h1>

[![Awpy Discord](https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord)](https://discord.gg/W34XjsSs2H) [![Awpy Downloads](https://static.pepy.tech/personalized-badge/awpy?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/awpy) [![Build](https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml/badge.svg)](https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml) [![Documentation Status](https://readthedocs.org/projects/awpy/badge/?version=latest)](https://awpy.readthedocs.io/en/latest/?badge=latest) [![MIT License](https://img.shields.io/badge/license-MIT-lightgrey)](https://github.com/pnxenopoulos/awpy/blob/main/LICENSE)

</div>

**Counter-Strike 2 Demo Parsing, Analytics and Visualization in Python**

- :computer: Parse Counter-Strike demos in Python in one line.
- :skull: Access kill, damage, grenade, bomb, player trajectory data, and more
- :chart: Calculate common statistics, such as ADR, KAST, Rating and win probability
- 🎞️ Visualize Counter-Strike data, including animated round gifs
- :speaker: Active [Discord](https://discord.gg/W34XjsSs2H) community

## Installation

To install Awpy, you can run

```
pip install awpy
```

> [!NOTE]
> `awpy` requires [Python](https://www.python.org/downloads/) >= 3.9. To update the library, just run `pip install --upgrade awpy`. To check your current version, run `pip freeze | grep awpy`.

> [!TIP]
> Don't worry if you get stuck, visit us [our Discord](https://discord.gg/W34XjsSs2H) for help.

## Example Code

Using Awpy is easy. Just find a demo you want to analyze and use the example below to get started. For example, take [NaVi vs Virtus.pro](https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro).

```python
from awpy import Demo

# Simply call `Demo(path="...")` to parse a demo
dem = Demo("natus-vincere-vs-virtus-pro-m1-overpass.dem")

# Access various dictionaries & dataframes
dem.header
dem.rounds
dem.grenades
dem.kills
dem.damages
dem.bomb
dem.smokes
dem.infernos
dem.weapon_fires
dem.ticks
```

> [!TIP]
> Want to learn more about the parser output? Visit the [parser primer](https://awpy.readthedocs.io/en/latest/parser_output.html) in our documentation!

### Help! The parser doesn't work or returns weird data

Counter-Strike demos can be a bit troublesome. It is likely you'll see increased error rates in POV demos. To help us address parsing issues, please open a bug report in our [Github issues](https://github.com/pnxenopoulos/awpy/issues) as well as in our [our Discord](https://discord.gg/3JrhKYcEKW). We're committed to increasing parsing coverage rates and appreciate any errors you may find.

## Examples and Projects

Take a look at the following Jupyter notebooks provided in our `examples/` directory. These will help you get started parsing and analyzing Counter-Strike data.

- [Parsing a CS2 demofile](https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CS2_Demofile.ipynb)

If you use the parser for any public analysis, we kindly ask you to link to the Awpy repository, so that others may know how you parsed, analyzed or visualized your data. If you have a paper or project that uses the parser, please let us know in Discord so we can add it to our growing list!

## Contributing

We welcome any contributions from the community, no matter the skill-level. You can visit our [issue page](https://github.com/pnxenopoulos/awpy/issues) to see what issues are still open, the [Awpy project](https://github.com/users/pnxenopoulos/projects/5) for a different view of project priorities, or you can message us on Discord. Some examples of where you can make a difference are in documentation, quality assurance, developing new features, or creating unique content with Awpy. You can see more examples of community content [here](https://awpy.readthedocs.io/en/latest/projects.html). If you are interested in contributing to Awpy, learn more [here](https://github.com/pnxenopoulos/awpy/blob/main/CONTRIBUTING.md).

> [!TIP]
> We are happy to walk through those that want to contribute, no matter your skill level. There are a diverse set of ways one can contribute to Awpy. We welcome first-time contributors.

## Structure

Awpy is structured as follows:

```
.
├── awpy
│   ├── data                      # Data directory (PLANNED)
│   ├── stats                     # Stats and analytics module
│   └── visualization             # Visualization module (PLANNED)
│   converters.py                 # Utilities for converting to readable strings
│   demo.py                       # Defines the base Demo class
│   parsers.py                    # Defines simple parsers for different events
│   utils.py                      # Utilities used across the project
├── doc                           # Documentation files
├── examples                      # Jupyter Notebooks showing example code
└── tests                         # Tests
```

## Acknowledgments

The name "Awpy" is due to [Nick Wan](https://www.twitch.tv/nickwan_datasci) -- we recommend his stream for sports data analytics enthusiasts.

Awpy was first built on the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) Golang library. We now rely on [demoparser2](https://github.com/LaihoE/demoparser) for parsing, which is another fantastic parsing project, built specifically for Python.
