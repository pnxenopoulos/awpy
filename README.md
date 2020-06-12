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
Using the `csgo` package is straightforward. 
easy. Just pick a demofile, and have a set of Pandas dataframes in seconds.

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
# which writes to competitionName_matchName_gameDate_gameTime_mapName.json
```

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
└── examples                      # Contains Jupyter Notebooks showing example code
```

## Requests and Issues
This project uses GitHub issues to track issues and feature requests. You can see open requests [here](https://github.com/pnxenopoulos/csgo/issues).

## Acknowledgements
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages. To fix errors brought about in the gonav package from Go 1.14, we provide an updated version in the [gonavparse](https://github.com/pnxenopoulos/csgonavparse).

## License
Our project is licensed using the [MIT License](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE).
