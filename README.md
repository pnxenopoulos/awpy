[![Build Status](https://travis-ci.com/pnxenopoulos/csgo.svg?branch=master)](https://travis-ci.com/pnxenopoulos/csgo) [![codecov](https://codecov.io/gh/pnxenopoulos/csgo/branch/master/graph/badge.svg)](https://codecov.io/gh/pnxenopoulos/csgo) [![MIT Licence](https://badges.frapsoft.com/os/mit/mit.svg?v=103)](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE)

# Analyzing Counter-Strike: Global Offensive Data
The `csgo` package provides data parsing, analytics and visualization capabilities for Counter-Strike: Global Offensive (CSGO) data. In this repository, you will find the source code, issue tracker and useful information pertaining to the `csgo` package.

## Setup
#### Requirements
`csgo` requires [Python](https://www.python.org/downloads/) >= 3.7 and [Golang](https://golang.org/dl/) >= 1.16. Python acts as a wrapper for the Go code which parses demofiles.

#### Installation
To install `csgo`, clone the repository and install it from source by running `python setup.py install`. *MAKE SURE TO HAVE GOLANG INSTALLED* (see above). 

## Example Code
Using the `csgo` package is straightforward. Just pick a demofile and have output in JSON or Pandas DataFrame form in seconds. Use the example below to get started.

```python
from csgo.parser import DemoParser

# Create parser object
# Set log=True above if you want to produce a logfile for the parser
# Set parse_rate to a power of 2 between 2^0 and 2^7. It indicates the spacing between parsed ticks. Larger numbers result in fewer frames recorded.
demo_parser = DemoParser(demofile="og-vs-natus-vincere-m1-dust2.dem", log=True, demo_id="og-vs-natus-vincere", parse_rate=128)


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
Take a look at the following Jupyter notebooks provided in our `examples/` directory.

- [Parsing a CSGO demofile](https://github.com/pnxenopoulos/csgo/blob/master/examples/00_Parsing_a_CSGO_Demofile.ipynb)
- [Basic CSGO analysis](https://github.com/pnxenopoulos/csgo/blob/master/examples/01_Basic_CSGO_Analysis.ipynb)

You can also look at the following papers which make use of the parser. If using the parser in research, please cite *Valuing Actions in Counter-Strike: Global Offensive* (first paper).

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
This project uses GitHub issues to track issues and feature requests. You can see open requests [here](https://github.com/pnxenopoulos/csgo/issues).

## Acknowledgments
This project is made possible by the amazing work done in the [demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) and [gonav](https://github.com/mrazza/gonav) packages. To fix errors brought about in the gonav package from Go 1.14, we provide an updated version in the [gonavparse](https://github.com/pnxenopoulos/csgonavparse).

## License
Our project is licensed using the [MIT License](https://github.com/pnxenopoulos/csgo/blob/master/LICENSE).
