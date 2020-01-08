# Counter-Strike: Global Offensive Analytics
The `csgo` package provides data parsing, analytics and visualization data structures and functions. In this repository, you will find the source code, issue tracker and useful information pertaining to the `csgo` package.

## Setup
### Requirements
`csgo` requires [Python 3](https://www.python.org/downloads/). Additionally, it requires installing [Go](https://golang.org/), which some of the backend parsing code uses. After installing Go, run

```
go get github.com/mrazza/gonav
go get github.com/markus-wa/demoinfocs-golang
```

### Installation
To install `csgo`, clone the repository and install it from source by doing `python setup.py sdist`.

## Structure
This repository contains code for CSGO analysis. It is structured as follows:

```
.
├── csgo                           
|   ├── parser                    # Code for CSGO demo parser
|   ├── analytics                 # Code for CSGO analysis
│   └── visualization             # Code for CSGO visualization
├── data
│   ├── map_img                   # Map images
│   └── original_nav_files        # Map navigation files
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

Each issue can be given a priority level by a repo-maintainer, such as High (red), Medium (yellow) and Low (green).

Please direct current queries to Peter Xenopoulos, at [xenopoulos@nyu.edu](mailto:xenopoulos@nyu.edu)

## Changelog:
Todo...
