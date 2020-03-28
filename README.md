[![Build Status](https://travis-ci.com/pnxenopoulos/csgo.svg?branch=master)](https://travis-ci.com/pnxenopoulos/csgo) [![MIT Licence](https://badges.frapsoft.com/os/mit/mit.svg?v=103)](https://opensource.org/licenses/mit-license.php) [![codecov](https://codecov.io/gh/pnxenopoulos/csgo/branch/master/graph/badge.svg)](https://codecov.io/gh/pnxenopoulos/csgo)

# Analyzing Counter-Strike: Global Offensive Data
The `csgo` package provides data parsing, analytics and visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and useful information pertaining to the `csgo` package.

## Setup
### Requirements
`csgo` requires [Python 3](https://www.python.org/downloads/). Additionally, it requires installing [Go](https://golang.org/), which some of the backend parsing code uses. After installing Go, run

```
go get github.com/mrazza/gonav
go get github.com/markus-wa/demoinfocs-golang
```

which downloads the necessary Go packages for the parsing backend.

### Installation
To install `csgo`, clone the repository and install it from source by doing `python setup.py install --user`.

### Tests
To run the tests, go to the root directory and run `python -m pytest -vv`.

## Example Code
Using the `csgo` package is easy. Just pick a demofile, and have a set of Pandas dataframes in seconds.

```python
from csgo.parser.match_parser import CSGOMatchParser

# Create parser object
match_parser = CSGOMatchParser(demofile = "demofile.dem", logfile = "parser.log", competition_name = "CompetitionName", match_name = "MatchName")

# Parse the demofile
match_parser.parse_demofile()

# If there is no demo error, start to parse
if not match_parser.demo_error:
    # Parse the match
    match_parser.parse_match()

    # Write the data frames
    match_parser.write_rounds()
    match_parser.write_kills()
    match_parser.write_damages()
    match_parser.write_bomb_events()
    match_parser.write_footsteps()

    # Access the data frames
    rounds = match_parser.rounds_df
    kills = match_parser.kills_df
    damages = match_parser.damages_df
    bomb_events = match_parser.bomb_df
    footsteps = match_parser.footsteps_df
```

## Structure
This repository contains code for CSGO analysis. It is structured as follows:

```
.
├── csgo
│   ├── analytics                 # Code for CSGO analysis
│   ├── data                      
│   │   ├── map_img               # Map images
│   │   └── original_nav_files    # Map navigation files
│   ├── parser                    # Code for CSGO demo parser
│   └── visualization             # Code for CSGO visualization
├── doc                           # Contains documentation, such as data dictionaries, etc.
└── examples                      # Contains Jupyter Notebooks showing example code
```

## Requests and Issues
This project uses GitHub issues to track issues. You can see open requests [here](https://github.com/pnxenopoulos/csgo/issues).

The types of issues are
- **BUGS**: Indicates something wrong with the code
- **DOCUMENTATION**: Indicates incorrect or missing documentation
- **FEATURE REQUEST**: Indicates a request for a new feature in the code
- **QUESTION**: Indicates a question about the parser or code

## Acknowledgements
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages.

## License
Our project is licensed using the [MIT License](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE).
