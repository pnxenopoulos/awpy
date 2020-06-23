package main

import (
	"flag"
	"fmt"
	"os"

	gonav "github.com/pnxenopoulos/csgonavparse"
)

func main() {
	fl := new(flag.FlagSet)

	navPathPtr := fl.String("map", "", "Map name `path`")
	areaIdX := fl.Int("area_x", 0, "First area id")
	areaIdY := fl.Int("area_y", 0, "Second area id")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	currentMap := *navPathPtr
	areaOne := *areaIdX
	areaTwo := *areaIdY

	startAreaId := uint32(areaOne)
	endAreaId := uint32(areaTwo)

	// Read in parser
	fNav, _ := os.Open("../data/nav/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()
	startArea := mesh.GetAreaById(startAreaId)
	endArea := mesh.GetAreaById(endAreaId)

	path, _ := gonav.SimpleBuildShortestPath(startArea, endArea)
	var areasVisited int = 0
	for _, currNode := range path.Nodes {
		if currNode != nil {
			areasVisited = areasVisited + 1
		}
	}
	fmt.Printf("%d\n", areasVisited)
}
