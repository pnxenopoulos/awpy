[![Build Status](https://travis-ci.com/pnxenopoulos/csgo.svg?branch=master)](https://travis-ci.com/pnxenopoulos/csgo) [![codecov](https://codecov.io/gh/pnxenopoulos/csgo/branch/master/graph/badge.svg)](https://codecov.io/gh/pnxenopoulos/csgo) [![MIT Licence](https://badges.frapsoft.com/os/mit/mit.svg?v=103)](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE)

# Analyzing Counter-Strike: Global Offensive Data
The `csgo` package provides data parsing, analytics and visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and useful information pertaining to the `csgo` package.

## Setup
### Requirements
`csgo` requires [Python](https://www.python.org/downloads/) >= 3.6 and [Golang](https://golang.org/dl/) >= 1.14. Python acts as a wrapper for the Go code which parses demofiles.

### Installation
To install `csgo`, clone the repository and install it from source by doing `python setup.py install`.

### Tests
To run the tests, go to the root directory and run `python -m pytest -vv`.

## Example Code
Using the `csgo` package is straightforward. Just pick a demofile and have a set of Pandas dataframes in seconds. Use the example below to get started.

```python
from csgo.parser import DemoParser

# Create parser object
# Set log=True above if you want to produce a logfile for the parser
demo_parser = DemoParser(demofile = "astralis-vs-liquid-m1-inferno.dem", match_id = "astralis-vs-liquid-m1-inferno.dem")


# Parse the demofile, output results to dictionary with df name as key
data = demo_parser.parse()

# The following keys exist
data["Rounds"]
data["Kills"]
data["Damages"]
data["Grenades"]
data["BombEvents"]
data["Footsteps"]

# You can also write the demofile data to JSON using
demo_parser.write_json()
# which writes to matchId_mapName.json
```

Alternatively, you can create an XML of the game, frame-by-frame, by doing
```python
from csgo.parser import FrameParser

# Create parser object
# Set log=True above if you want to produce a logfile for the parser
demo_frame_parser = FrameParser(demofile = "astralis-vs-liquid-m1-inferno.dem", match_id = "astralis-vs-liquid-m1-inferno.dem")

# Parse the demofile, output results match_id.xml
demo_frame_parser.parse()
```

## Examples
Take a look at the following Jupyter notebooks provided in our `examples/` directory.

- [Parsing a CSGO demofile](https://github.com/pnxenopoulos/csgo/blob/master/examples/00_Parsing_a_CSGO_demofile.ipynb)
- [Basic CSGO analysis](https://github.com/pnxenopoulos/csgo/blob/master/examples/01_Basic_statistical_analysis.ipynb)
- [Creating game frames](https://github.com/pnxenopoulos/csgo/blob/master/examples/02_Generating_game_frames.ipynb)

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
This project uses GitHub issues to track issues and feature requests. You can see open requests [here](https://github.com/pnxenopoulos/csgo/issues).

## Acknowledgements
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages. To fix errors brought about in the gonav package from Go 1.14, we provide an updated version in the [gonavparse](https://github.com/pnxenopoulos/csgonavparse).

## License
Our project is licensed using the [MIT License](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE).
