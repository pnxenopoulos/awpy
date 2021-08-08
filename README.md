[![Chat](https://img.shields.io/badge/chat-on%20discord-7289da.svg)](https://discord.gg/3JrhKYcEKW) [![MIT Licence](https://badges.frapsoft.com/os/mit/mit.svg?v=103)](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE)

# Analyzing Counter-Strike: Global Offensive Data
The `csgo` package provides data parsing, analytics and (soon) visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and other useful information pertaining to the `csgo` package. Please join [our Discord](https://discord.gg/3JrhKYcEKW) for discussion around the library, along with other resources for esports analytics.

## Setup
#### Requirements
`csgo` requires [Python](https://www.python.org/downloads/) >= 3.7 and [Golang](https://golang.org/dl/) >= 1.16. Python acts as a wrapper for the Go code which parses demofiles.

#### Installation
To install `csgo`, clone the repository by running `git clone https://github.com/pnxenopoulos/csgo`. Then, change directories to the newly cloned repository, and install the library by running `python setup.py install`. For more help, you can visit the installation channel in our Discord.

## Example Code
Using the `csgo` package is straightforward. Just choose a demofile and have output in a JSON or Pandas DataFrame in a few seconds. Use the example below to get started.

```python
from csgo.parser import DemoParser


# Set parse_rate to a power of 2 between 2^0 and 2^7. It indicates the spacing between parsed ticks. Larger numbers result in fewer frames recorded. 128 indicates a frame per second on professional game demos.
demo_parser = DemoParser(demofile="og-vs-natus-vincere-m1-dust2.dem", demo_id="og-vs-natus-vincere", parse_rate=128)


# Parse the demofile, output results to dictionary with df name as key
data = demo_parser.parse()


# The following keys exist
data["MatchId"]
data["ClientName"]
data["MapName"]
data["TickRate"]
data["PlaybackTicks"]
data["GameRounds"]

# You can also parse the data into dataframes using
data_df = demo_parser.parse(return_type="df")


# You can also access the data in the file demoId_mapName.json, which is written in your working directory
```

## Examples and Papers
Take a look at the following Jupyter notebooks provided in our `examples/` directory. These will help you get started parsing and analyzing CSGO data.

- [Parsing a CSGO demofile](https://github.com/pnxenopoulos/csgo/blob/master/examples/00_Parsing_a_CSGO_Demofile.ipynb)
- [Basic CSGO analysis](https://github.com/pnxenopoulos/csgo/blob/master/examples/01_Basic_CSGO_Analysis.ipynb)

You can also look at the following papers which make use of the parser. If using the parser in research, please cite *Valuing Actions in Counter-Strike: Global Offensive* (first paper). If you have a paper that uses the parser, please let us know in Discord so we can add it!

Xenopoulos, Peter, et al. "[Valuing Actions in Counter-Strike: Global Offensive](https://arxiv.org/pdf/2011.01324.pdf)." 2020 IEEE International Conference on Big Data (Big Data). IEEE, 2020.

Xenopoulos, Peter, et al. "[ggViz: Accelerating Large-Scale Esports Game Analysis](https://arxiv.org/pdf/2107.06495.pdf)."


## Structure
This repository contains code for CSGO analysis. It is structured as follows:

```
.
├── csgo
│   ├── analytics                 # Code for CSGO analysis
│   ├── data                      
│   │   ├── map                   # Map images
│   │   └── nav                   # Map navigation files
│   ├── parser                    # Code for CSGO demo parser
│   └── visualization             # Code for CSGO visualization
├── doc                           # Contains documentation, such as data dictionaries, etc.
├── examples                      # Contains Jupyter Notebooks showing example code
└── tests                         # Contains tests for the csgo package
```

## Requests and Issues
This project uses GitHub issues to track issues and feature requests. You can see open requests [here](https://github.com/pnxenopoulos/csgo/issues). If you come across a bug, please open an issue, and also consider bringing it to the community's attention in the Discord. Same goes for feature requests. Please checkout the `dev` branch to work on the library.

## Acknowledgments
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages. To fix errors brought about in the gonav package from Go 1.14, we provide an updated version in the [gonavparse](https://github.com/pnxenopoulos/csgonavparse).
