# The csgo Python package
The `csgo` package provides data parsing, analytics and visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and useful information pertaining to the `csgo` package.

## Setup
### Requirements
`csgo` requires [Python 3](https://www.python.org/downloads/). Additionally, it requires installing [Go](https://golang.org/), which some of the backend parsing code uses. After installing Go, run

```
go get github.com/mrazza/gonav
go get github.com/markus-wa/demoinfocs-golang
```

### Installation
To install `csgo`, clone the repository and install it from source by doing `python setup.py install --user`.

## Structure
This repository contains code for CSGO analysis. It is structured as follows:

```
.
├── csgo              
|   ├── data
│       ├── map_img               # Map images
│       └── original_nav_files    # Map navigation files             
|   ├── parser                    # Code for CSGO demo parser
|   ├── analytics                 # Code for CSGO analysis
│   └── visualization             # Code for CSGO visualization
├── data
│   ├── map_img                   # Map images
│   └── original_nav_files        # Map navigation files
├── doc                           # Contains documentation, such as data dictionaries, etc.
└── examples                      # Contains Jupyter Notebooks showing example code
```

## Example Code
Using the `csgo` package is easy. Just pick a demofile, and have a set of Pandas dataframes in seconds.

```python
from csgo.parser.match_parser import CSGOMatchParser

# Create parser object
match_parser = CSGOMatchParser(demofile = "demofile.dem", logfile = "parser.log", competition_name = "CompetitionName", match_name = "MatchName")

# Parse the demofile
p.parse_demofile()

# If there is no demo error, start to parse
if not p.demo_error:
	# Find the demo start line
	p.find_match_start()

	# Parse the match
    p.parse_match()

    # Write the data frames
    p.write_rounds()
    p.write_kills()
    p.write_damages()
    p.write_bomb_events()
    p.write_footsteps()

    # Access the data frames
    rounds = p.rounds_df
    kills = p.kills_df
    damages = p.damages_df
    bomb_events = p.bomb_df
    footsteps = p.footsteps_df
```

## Requests and Issues
This project uses GitHub issues to track issues. You can see open requests [here](https://github.com/pnxenopoulos/csgo/issues).

The types of issues are
- **BUGS**: Indicates something wrong with the code
- **DOCUMENTATION**: Indicates incorrect or missing documentation
- **FEATURE REQUEST**: Indicates a request for a new feature in the code
- **QUESTION**: Indicates a question about the parser or code

Each issue can be given a priority level by a repo-maintainer, such as High (red), Medium (yellow) and Low (green).

Please direct current queries to Peter Xenopoulos, at [xenopoulos@nyu.edu](mailto:xenopoulos@nyu.edu)

## Acknowledgements
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages.
