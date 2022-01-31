[![Discord](https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord)](https://discord.gg/W34XjsSs2H) [![Build](https://github.com/pnxenopoulos/csgo/actions/workflows/build.yml/badge.svg)](https://github.com/pnxenopoulos/csgo/actions/workflows/build.yml) [![Documentation Status](https://readthedocs.org/projects/pycsgo/badge/?version=latest)](https://pycsgo.readthedocs.io/en/latest/?badge=latest) [![Docs](https://img.shields.io/badge/docs-Documentation-informational)](https://pycsgo.readthedocs.io/en/latest/) [![GitHub issues](https://img.shields.io/github/issues/pnxenopoulos/csgo)](https://github.com/pnxenopoulos/csgo/issues) [![MIT Licence](https://img.shields.io/badge/license-MIT-lightgrey)](https://github.com/pnxenopoulos/csgo/blob/main/LICENSE)

# Analyzing Counter-Strike: Global Offensive Data
The `csgo` package provides data parsing, analytics and visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and other useful information pertaining to the `csgo` package. Please join [our Discord](https://discord.gg/W34XjsSs2H) for discussion around the library, along with other resources for esports analytics. 

## Table of Contents
[Setup and Installation](#setup)

[Example Code and Projects](#example-code)

[Contributing](#contributing)

[Structure](#structure)

[Acknowledgments](#acknowledgments)

## Setup
#### Requirements
`csgo` requires [Python](https://www.python.org/downloads/) >= 3.8 and [Golang](https://golang.org/dl/) >= 1.17. Python acts as a wrapper for the Go code which parses demofiles.

#### Installation
To install `csgo`, you can run `pip install git+https://github.com/pnxenopoulos/csgo@main`. To update the library, just run the command again. For more help, you can visit the installation channel in our Discord.

#### Colab Notebook
Do your work in Colab? No problem, the csgo Python library runs there, too. Check out how to [setup csgo Python library in Google Colab](https://colab.research.google.com/drive/1xiXeWHSAlqYNa-xjSK9B2xalvLMpIlJF?usp=sharing).

## Example Code
Using the `csgo` package is straightforward. Just choose a demofile and have output in a JSON or Pandas DataFrame in a few seconds. Use the example below to get started.

```python
from csgo.parser import DemoParser


# Set parse_rate to a power of 2 between 2^0 and 2^7. It indicates the spacing between parsed ticks. Larger numbers result in fewer frames recorded. 128 indicates a frame per second on professional game demos.
demo_parser = DemoParser(demofile="og-vs-natus-vincere-m1-dust2.dem", demo_id="og-vs-natus-vincere", parse_rate=128)


# Parse the demofile, output results to dictionary with df name as key
data = demo_parser.parse()


# The following keys exist
data["matchID"]
data["clientName"]
data["mapName"]
data["tickRate"]
data["playbackTicks"]
data["parserParameters"]
data["serverVars"]
data["matchPhases"]
data["parsedPlaceNames"]
data["matchmakingRanks"]
data["gameRounds"] # From this value, you can extract player events via: data['gameRounds'][i]['kills'], etc.

# You can also parse the data into dataframes using
data_df = demo_parser.parse(return_type="df")


# You can also access the data in the file demoId_mapName.json, which is written in your working directory
```

### Help! The parser returns weird rounds.
Please note that the parser parses _everything_ in the demo. This means that you may have rounds from the warmup (denoted with the `isWarmup` flag), rounds that may have ended in a draw, and other odd-looking rounds. Try using the `DemoParser.clean_rounds()` method to clean up. Note that this is not going to be 100 percent perfect.

### Help! The parser doesn't work or lacks a feature
If you need help with the parser, join our [Discord](https://discord.gg/3JrhKYcEKW). CSGO demos are oftentimes imperfect, but if you ask on Discord, we can try to figure out what the problem is. Also, note the help section above. If you come across any issue, whether a demo doesn't parse, parsed demo data is incorrect or you want a new feature, do not hesitate to open an issue or ask on [Discord](https://discord.gg/W34XjsSs2H). You can see open issues [here](https://github.com/pnxenopoulos/csgo/issues) and can visit [our documentation](https://pycsgo.readthedocs.io/en/latest/) for more information on the library's capabilities.

## Examples and Projects
Take a look at the following Jupyter notebooks provided in our `examples/` directory. These will help you get started parsing and analyzing CSGO data.

- [Parsing a CSGO demofile](https://github.com/pnxenopoulos/csgo/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb)
- [Basic CSGO analysis](https://github.com/pnxenopoulos/csgo/blob/main/examples/01_Basic_CSGO_Analysis.ipynb)
- [CSGO visualization](https://github.com/pnxenopoulos/csgo/blob/main/examples/02_Basic_CSGO_Visualization.ipynb)
- [Working with navigation meshes.ipynb](https://github.com/pnxenopoulos/csgo/blob/main/examples/03_Working_with_Navigation_Meshes.ipynb)

If you use the parser in research, please cite *Valuing Actions in Counter-Strike: Global Offensive*, below. If you use the parser for any analysis on Twitter, we kindly ask you to cite back to the parser, so that others may know how you parsed your data. If you have a paper that uses the parser, please let us know in Discord so we can add it! Here is the paper citation:

Xenopoulos, Peter, et al. "[Valuing Actions in Counter-Strike: Global Offensive](https://arxiv.org/pdf/2011.01324.pdf)." 2020 IEEE International Conference on Big Data (Big Data). IEEE, 2020.

## Contributing
We welcome any contributions from the community. You can visit the issue page to see what issues are still open, or you can message on Discord. We will always have a need for writing tests and expanding functionality. Currently, we are focused on refining our tests and on building more visualization functions. We also see contributors as those who use the library to produce interesting content (such as tweets, analyses, papers, etc.) -- you can see more examples of community content [here](https://github.com/pnxenopoulos/csgo/blob/main/docs/projects.md).

When contributing code, be sure to lint your code using `black`, and to run the tests using `pytest`.

## Structure
This csgo Python library is structured as follows:

```
.
├── csgo
│   ├── analytics                 # Code for CSGO analytics
│   ├── data                      
│   │   ├── map                   # Map images, map data
│   │   └── nav                   # Map navigation files
│   ├── parser                    # Code for CSGO demo parser
│   └── visualization             # Code for CSGO visualization
├── doc                           # Contains documentation markdown files
├── examples                      # Contains Jupyter Notebooks showing example code
└── tests                         # Contains tests for the csgo package
```

## Acknowledgments
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages. To fix errors brought about in the gonav package from Go 1.14, we provide an updated version in the [gonavparse](https://github.com/pnxenopoulos/csgonavparse).

Big shoutout to [SimpleRadar](https://readtldr.gg/simpleradar?utm_source=github&utm_id=xenos-csgo-parser) for allowing use of their map images.

Special thanks to [arjun-22](https://github.com/arjun-22) for his work on the stats module and expanding test coverage.
