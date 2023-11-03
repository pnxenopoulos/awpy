<table style="border-collapse: collapse; border: 0px solid black;">
  <tr>
    <td align="center"><img src="https://www.counter-strike.net/favicon.ico" alt="Counter Strike 2" style="max-width: 30%; max-height: 30%;"></td>
    <td align="center">
      <p style="font-size: 32px; font-weight: bold;">Awpy</p>
      <p style="font-size: 16px;">Demo Parsing, Analytics and Visualization for Counter Strike</p>
      <p>
        <a href="https://discord.gg/W34XjsSs2H"><img src="https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord" alt="Awpy Discord"></a>
        <a href="https://pepy.tech/project/awpy"><img src="https://static.pepy.tech/personalized-badge/awpy?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads" alt="Awpy Downloads"></a>
        <a href="https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml"><img src="https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml/badge.svg" alt="Build"></a>
        <a href="https://awpy.readthedocs.io/en/latest/?badge=latest"><img src="https://readthedocs.org/projects/awpy/badge/?version=latest" alt="Documentation Status"></a>
        <a href="https://github.com/pnxenopoulos/awpy/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT Licence"></a>
    </p>
    </td>
  </tr>
</table>

---

The `awpy` Python package provides data parsing, analytics and visualization capabilities for Counter-Strike 2 data. Awpy contains functionality to parse (kills, damages, grenades, etc.), analyze (win probability, Rating, KAST%, ADR, etc.), and visualize (animated plots, grenade diagrams, etc.) CS2 demos. Please join [our Discord](https://discord.gg/W34XjsSs2H) for discussion around the library and esports analytics. You may visit detailed documentation [here](https://awpy.readthedocs.io/en/latest/).

## Table of Contents
[Installation](#setup)

[Example Code and Projects](#example-code)

[Contributing](#contributing)

[Structure](#structure)

[Acknowledgments](#acknowledgments)

## Installation
To install `awpy`, you can run

```
pip install awpy
```

`awpy` requires [Python](https://www.python.org/downloads/) >= 3.11. To update the library, just run `pip install --upgrade awpy`. 

:bulb: **Tip:** Don't worry if you get stuck, visit us [our Discord](https://discord.gg/W34XjsSs2H) for help.

#### Colab Notebook
Do you work in Google Colab? No problem, the `awpy` Python library runs there, too! Check out how to [setup awpy Python library in Google Colab](https://colab.research.google.com/drive/1xiXeWHSAlqYNa-xjSK9B2xalvLMpIlJF?usp=sharing).

## Example Code
Using the `awpy` package is straightforward. Just grab a demofile and have output in a JSON or Pandas DataFrame in a few seconds. Use the example below to get started.

```python
from awpy import parse_demo

# Awpy parsed into a dictionary of data frames
parsed_dfs = parse_demo("cool-hltv-demo.dem")

# Demo info such as map, server, etc.
parsed["header"]

# Round start/end ticks, along with round end reasons
parsed["rounds"]

# Kill, damage, and weapon fire events
parsed["kills"]
parsed["damages"]
parsed["weapon_fires"]

# Effects, such as infernos (fires) and smokes
parsed["effects"]

# All bomb events, such as plants and defuses
parsed["bomb_events"]

# Every time a player was blinded and for how long
parsed["flashes"]

# Trajectories of all grenades
parsed["grenades"]

# Information on every player at every tick
parsed["ticks"]
```

### Help! The parser doesn't work or returns weird data
CS2 demos can be a bit troublesome. It is likely you'll see increased error rates in POV demos. To help us gain more datapoints to hunt down parsing bugs, please raise a bug report in our [Github issues](https://github.com/pnxenopoulos/awpy/issues) or in our [our Discord](https://discord.gg/3JrhKYcEKW). We're committed to increasing parsing coverage rates and appreciate any errors you may find. You can also check [our documentation](https://awpy.readthedocs.io/en/latest/).

## Examples and Projects
Take a look at the following Jupyter notebooks provided in our `examples/` directory. These will help you get started parsing and analyzing CSGO data.

- [Parsing a CSGO demofile](https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb)
- [Basic CSGO analysis](https://github.com/pnxenopoulos/awpy/blob/main/examples/01_Basic_CSGO_Analysis.ipynb)
- [Basic CSGO visualization](https://github.com/pnxenopoulos/awpy/blob/main/examples/02_Basic_CSGO_Visualization.ipynb)
- [Working with navigation meshes](https://github.com/pnxenopoulos/awpy/blob/main/examples/03_Working_with_Navigation_Meshes.ipynb)
- [Advanced navigation functionality](https://github.com/pnxenopoulos/awpy/blob/main/examples/04_Advanced_Navigation_Functionality.ipynb)
- [Map control](https://github.com/pnxenopoulos/awpy/blob/main/examples/05_Map_Control_Calculations_And_Visualizations.ipynb)

If you use the parser for any public analysis, we kindly ask you to link to this repository, so that others may know how you parsed, analyzed or visualized your data. If you have a paper or project that uses the parser, please let us know in Discord so we can add it!

## Contributing
We welcome any contributions from the community. You can visit the [issue page](https://github.com/pnxenopoulos/awpy/issues) to see what issues are still open, or you can message mods on Discord. If you're new to contributed, don't worry! We will always have a need for writing tests, quality assurance, and documentation, which are great beginner tasks. We also seek contributors to produce interesting content (such as tweets, analyses, papers, etc.) -- you can see more examples of community content [here](https://awpy.readthedocs.io/en/latest/projects.html). If you are interested in contributing to Awpy, learn more [here](https://github.com/pnxenopoulos/awpy/blob/main/CONTRIBUTING.md). We are big fans of tools like [black](https://github.com/psf/black), [ruff](https://github.com/charliermarsh/ruff), [pylint](https://github.com/pylint-dev/pylint) and [pyright](https://microsoft.github.io/pyright/).

## Structure
`awpy` is structured as follows:

```
.
├── awpy
│   ├── analytics                 # Code for Counter-Strike analytics
│   ├── data                      # Code for dealing with Counter-Strike map and nav data
│   ├── parser                    # Code for Counter-Strike demo parser
│   └── visualization             # Code for Counter-Strike visualization
├── doc                           # Contains documentation files
├── examples                      # Contains Jupyter Notebooks showing example code
└── tests                         # Contains tests for the awpy package
```

## Acknowledgments

The name "Awpy" is due to [Nick Wan](https://www.twitch.tv/nickwan_datasci) -- we recommend his stream for sports data analytics enthusiasts. 

Awpy was first built on the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang). We now rely on [demoparser2](https://github.com/LaihoE/demoparser) for parsing, which is another fantastic parsing project.

Thanks to [SimpleRadar](https://readtldr.gg/simpleradar?utm_source=github&utm_id=xenos-csgo-parser) for allowing use of their map images in the visualization module.

#### List of Contributors

- [Jan-Eric](https://github.com/JanEricNitschke)
- [Adi](https://twitter.com/AdiSujithkumar)
- [hojlund](https://github.com/hojlund123)
- [arjun-22](https://github.com/arjun-22)

Additional thanks to those of you in the Discord community who file bug reports and test awpy thoroughly.







