<div align="center">
<h1>Awpy</h1>

[![Awpy Discord](https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord)](https://discord.gg/W34XjsSs2H) [![Awpy Downloads](https://static.pepy.tech/personalized-badge/awpy?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/awpy) [![Build](https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml/badge.svg)](https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml) [![Artifacts](https://github.com/pnxenopoulos/awpy/actions/workflows/artifacts.yml/badge.svg)](https://github.com/pnxenopoulos/awpy/actions/workflows/artifacts.yml) [![Documentation Status](https://readthedocs.org/projects/awpy/badge/?version=latest)](https://awpy.readthedocs.io/en/latest/?badge=latest) [![MIT License](https://img.shields.io/badge/license-MIT-lightgrey)](https://github.com/pnxenopoulos/awpy/blob/main/LICENSE)

</div>

**Counter-Strike 2 Demo Parsing, Analytics and Visualization in Python**

- :computer: Parse Counter-Strike demos in Python or with a command-line interface
- :skull: Access tick-level player and event data, like kills, damages and more
- :chart: Calculate popular statistics, such as ADR, KAST and Rating
- :mag_right: Determine player visibility in microseconds
- :earth_americas: Parse navigation meshes (.nav) and calculate distance metrics
- 🎞️ Visualize Counter-Strike data, including animated round gifs and heatmaps
- :speaker: Active [Discord](https://discord.gg/W34XjsSs2H) community

## Installation

To install Awpy, you can run

```
pip install awpy
```

> [!NOTE]
> Awpy requires [Python](https://www.python.org/downloads/) >= 3.11. To update the library, just run `pip install --upgrade awpy`. To check your current Awpy version, run `pip show awpy`. If you want to see what data is available for download, run `awpy get --help`.

> [!TIP]
> Don't worry if you get stuck, visit [our Discord](https://discord.gg/W34XjsSs2H) for help.

## Example Code

Using Awpy is easy. Just find a demo you want to analyze and use the example below to get started. You can easily find demos on [HLTV](https://hltv.org), [FACEIT](https://faceit.com) or [CS2Stats](https://csstats.gg/).

```python
from awpy import Demo

# Create and parse demo
dem = Demo("g2-vs-navi.dem")
dem.parse()

# Access various dictionaries & dataframes
dem.header
dem.rounds
dem.grenades
dem.kills
dem.damages
dem.bomb
dem.smokes
dem.infernos
dem.shots
dem.footsteps
dem.ticks

# The dataframes are Polars dataframes
# to transform to Pandas, just do .to_pandas()
dem.ticks.to_pandas()
```

> [!TIP]
> Want to learn more about the parser output? Visit the [parser primer](https://awpy.readthedocs.io/en/latest/modules/parser_output.html) in our documentation!

### Help! The parser doesn't work or returns weird data

Counter-Strike demos can be a bit troublesome. It is likely you'll see increased error rates in POV demos. To help us address parsing issues, please open a bug report in our [Github issues](https://github.com/pnxenopoulos/awpy/issues). Additionally, you can reach out in [our Discord](https://discord.gg/3JrhKYcEKW). We're appreciate any help in identifying bugs. We use [LaihoE's demoparser](https://github.com/LaihoE/demoparser) as a backend, so you may also check there for any open issues.

## Examples and Projects

Take a look at the following Jupyter notebooks provided in our `examples/` directory. These will help you get started parsing and analyzing Counter-Strike data.

- [Parsing a CS2 demofile](https://awpy.readthedocs.io/en/latest/examples/parse_demo.html)
- [Parsing a CS2 demofile through command-line](https://awpy.readthedocs.io/en/latest/examples/parse_demo_cli.html)
- [Calculating ADR, KAST% and Rating](https://awpy.readthedocs.io/en/latest/examples/demo_stats.html)
- [Plotting CS2 demos](https://awpy.readthedocs.io/en/latest/examples/plot_demo.html)
- [Calculating visibility from CS2 demos](https://awpy.readthedocs.io/en/latest/examples/visibility.html)
- [Parsing CS2 `.nav` files](https://awpy.readthedocs.io/en/latest/examples/nav.html)

If you use the parser for any public analysis, we kindly ask you to link to the Awpy repository, so that others may know how you parsed, analyzed or visualized your data. If you have a paper or project that uses the parser, please let us know in Discord so we can add it to our growing list!

> [!IMPORTANT]
> If you use Awpy, we'd love if you could link back to our repo!

## Contributing

We welcome any contributions from the community, no matter the skill-level. You can visit our [issue page](https://github.com/pnxenopoulos/awpy/issues) to see what issues are still open, the [Awpy project](https://github.com/users/pnxenopoulos/projects/5) for a different view of project priorities, or you can message us on Discord. Some examples of where you can make a difference are in documentation, quality assurance, developing new features, or creating unique content with Awpy. You can see more examples of community content [here](https://awpy.readthedocs.io/en/latest/projects.html). If you are interested in contributing to Awpy, learn more [here](https://github.com/pnxenopoulos/awpy/blob/main/CONTRIBUTING.md).

> [!TIP]
> We are happy to walk through those that want to contribute, no matter your skill level. There are a diverse set of ways one can contribute to Awpy. We welcome first-time contributors!

## Acknowledgments

The name "Awpy" is due to [Nick Wan](https://www.twitch.tv/nickwan_datasci) -- we recommend his stream for sports data analytics enthusiasts.

Awpy was first built on the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) Golang library. We now rely on [demoparser2](https://github.com/LaihoE/demoparser) for parsing, which is another fantastic parsing project, built specifically for Python.

Awpy's team includes JanEric, adi and hojlund, who you can find in the Awpy Discord. Their work, among others, is crucial to Awpy's continued success! To contribute to Awpy, please visit [CONTRIBUTING](https://github.com/pnxenopoulos/awpy/blob/main/CONTRIBUTING.md).
