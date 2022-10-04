[![Discord](https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord)](https://discord.gg/W34XjsSs2H) [![Downloads](https://static.pepy.tech/personalized-badge/awpy?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/awpy) [![Build](https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml/badge.svg)](https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml) [![Documentation Status](https://readthedocs.org/projects/awpy/badge/?version=latest)](https://awpy.readthedocs.io/en/latest/?badge=latest) [![Docs](https://img.shields.io/badge/docs-Documentation-informational)](https://awpy.readthedocs.io/en/latest/) [![GitHub issues](https://img.shields.io/github/issues/pnxenopoulos/awpy)](https://github.com/pnxenopoulos/awpy/issues) [![MIT Licence](https://img.shields.io/badge/license-MIT-lightgrey)](https://github.com/pnxenopoulos/awpy/blob/main/LICENSE)


# awpy
The `awpy` package provides data parsing, analytics and visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and other useful `awpy` information. Please join [our Discord](https://discord.gg/W34XjsSs2H) for discussion around the library and esports analytics. You may visit the documentation [here](https://awpy.readthedocs.io/en/latest/).

## Table of Contents
[Setup and Installation](#setup)

[Example Code and Projects](#example-code)

[Contributing](#contributing)

[Structure](#structure)

[Acknowledgments](#acknowledgments)

## Setup
#### Requirements
`awpy` requires [Python](https://www.python.org/downloads/) >= 3.8 and [Golang](https://golang.org/dl/) >= 1.17. Python acts as a wrapper for the Go code which parses demofiles.

#### Installation
To install `awpy`, you can run

```
pip install awpy
```

To update the library, just run the command again. For more help, you can visit the installation channel in [our Discord](https://discord.gg/W34XjsSs2H).

#### Colab Notebook
Do your work in Colab? No problem, the `awpy` Python library runs there, too. Check out how to [setup awpy Python library in Google Colab](https://colab.research.google.com/drive/1xiXeWHSAlqYNa-xjSK9B2xalvLMpIlJF?usp=sharing).

## Example Code
Using the `awpy` package is straightforward. Just grab a demofile and have output in a JSON or Pandas DataFrame in a few seconds. Use the example below to get started.

```python
from awpy import DemoParser

# Set the parse_rate equal to the tick rate at which you would like to parse the frames of the demo.
# This parameter only matters if parse_frames=True ()
# For reference, MM demos are usually 64 ticks, and pro/FACEIT demos are usually 128 ticks.
demo_parser = DemoParser(demofile="og-vs-natus-vincere-m1-dust2.dem", demo_id="og-vs-natus-vincere", parse_rate=128)


# Parse the demofile, output results to dictionary with df name as key
data = demo_parser.parse()


# There are a variety of top level keys
# You can view game rounds and events in 'gameRounds']
data["matchID"]
data["clientName"]
data["mapName"]
data["tickRate"]
data["playbackTicks"]
data["playbackFramesCount"]
data["parsedToFrameIdx"]
data["parserParameters"]
data["serverVars"]
data["matchPhases"]
data["matchmakingRanks"]
data["playerConnections"]
data["gameRounds"] # From this value, you can extract player events via: data['gameRounds'][i]['kills'], etc.

# You can also parse the data into dataframes using
data_df = demo_parser.parse(return_type="df")


# The parser also writes a JSON file of the output named demo_id.json
```

### Help! The parser returns weird rounds.
Please note that the parser parses _everything_ in the demo. This means that you may have rounds from the warmup (denoted with the `isWarmup` flag), rounds that may have ended in a draw, and other odd-looking rounds. Try using the `DemoParser.clean_rounds()` method to clean up. Note that this is not going to be 100 percent perfect.

### Help! The parser doesn't work or lacks a feature
If you need help with the parser, join [our Discord](https://discord.gg/3JrhKYcEKW). CSGO demos are oftentimes imperfect, but if you ask on Discord, we can try to figure out what is the problem. Please remember to post the error and demo if you can! You can also check the [open issues](https://github.com/pnxenopoulos/awpy/issues) or visit visit [our documentation](https://awpy.readthedocs.io/en/latest/).

## Examples and Projects
Take a look at the following Jupyter notebooks provided in our `examples/` directory. These will help you get started parsing and analyzing CSGO data.

- [Parsing a CSGO demofile](https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb)
- [Basic CSGO analysis](https://github.com/pnxenopoulos/awpy/blob/main/examples/01_Basic_CSGO_Analysis.ipynb)
- [Basic CSGO visualization](https://github.com/pnxenopoulos/awpy/blob/main/examples/02_Basic_CSGO_Visualization.ipynb)
- [Working with navigation meshes](https://github.com/pnxenopoulos/awpy/blob/main/examples/03_Working_with_Navigation_Meshes.ipynb)

If you use the parser for any analysis on Twitter, we kindly ask you to link to this repository, so that others may know how you parsed your data. If you have a paper or project that uses the parser, please let us know in Discord so we can add it!

## Contributing
We welcome any contributions from the community. You can visit the [issue page](https://github.com/pnxenopoulos/awpy/issues) to see what issues are still open, or you can message on Discord. We will always have a need for writing tests, quality assurance and expanding functionality. We also seek contributors to produce interesting content (such as tweets, analyses, papers, etc.) -- you can see more examples of community content [here](https://awpy.readthedocs.io/en/latest/projects.html).

When contributing code, be sure to lint your code using `black`, run the tests using `pytest`, and add any documentation (main module are automatically covered, just make sure you write the documentation in the function).

## Structure
`awpy` is structured as follows:

```
.
├── awpy
│   ├── analytics                 # Code for CSGO analytics
│   ├── data                      # Code for dealing with CSGO map and nav data
│   ├── parser                    # Code for CSGO demo parser
│   └── visualization             # Code for CSGO visualization
├── doc                           # Contains documentation files
├── examples                      # Contains Jupyter Notebooks showing example code
└── tests                         # Contains tests for the awpy package
```

## Acknowledgments
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang).

Big shoutout to [SimpleRadar](https://readtldr.gg/simpleradar?utm_source=github&utm_id=xenos-csgo-parser) for allowing use of their map images.

Special thanks to [arjun-22](https://github.com/arjun-22) for his work on the stats module and expanding test coverage.

Thanks to [Jan-Eric](https://github.com/JanEricNitschke) for his contributions extending the navigation functionality.

Additional thanks to those of you in the Discord community who file bug reports and test awpy thoroughly.
