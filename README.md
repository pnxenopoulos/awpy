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
demo_parser = DemoParser(demofile = "demofile.dem", competition_name = "CompetitionName", match_name = "MatchName", game_date="00-00-0000", game_time="00:00")
# Set arg log=True above if you want to produce a logfile for the parser

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

Alternatively, sites like HLTV release compressed folders with multiple demofiles corresponding to a single match. The `csgo` package can handle these as well.

```python
from csgo.parser import MatchParser

# Create MatchParser, pass the uncompressed directory of demofiles to the arg match_dir
match_parser = MatchParser(match_dir="demoDir/", competition_name = "CompetitionName", match_name = "MatchName", game_date="00-00-0000", game_time="00:00")

# Parse the directory
match_data = match_parser.parse()

# Data will be accessible in the keys of match_data, which correspond to the map of each parsed demofile. 
# For example, say the match took place over three maps, de_dust2, de_nuke and de_train, then we could access the data by doing
match_data["de_nuke"]
match_data["de_dust2"]
match_data["de_train"]

# We can write a JSON when we parse by doing
game_data = match_parser.parse(write_json=True)
# which writes to competitionName_matchName_gameDate_gameTime.json
# and has the game data in each of the keys corresponding to each map
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
