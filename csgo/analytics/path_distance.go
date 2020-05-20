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
	startXPtr := fl.Float64("start_x", 0, "Start X")
	startYPtr := fl.Float64("start_y", 0, "Start Y")
	startZPtr := fl.Float64("start_z", 0, "Start Z")
	endXPtr := fl.Float64("end_x", 0, "End X")
	endYPtr := fl.Float64("end_y", 0, "End Y")
	endZPtr := fl.Float64("end_z", 0, "End Z")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	currentMap := *navPathPtr
	startX := *startXPtr
	startY := *startYPtr
	startZ := *startZPtr
	endX := *endXPtr
	endY := *endYPtr
	endZ := *endZPtr

	// Read in args
	//currentMap, startX, startY, startZ, endX, endY, endZ = DemoPathFromArgs()
	// Read in parser
	fNav, _ := os.Open("../data/nav/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()
	startLoc := gonav.Vector3{X: float32(startX), Y: float32(startY), Z: float32(startZ)}
	endLoc := gonav.Vector3{X: float32(endX), Y: float32(endY), Z: float32(endZ)}
	startArea := mesh.GetNearestArea(startLoc, true)
	endArea := mesh.GetNearestArea(endLoc, true)

	path, _ := gonav.SimpleBuildShortestPath(startArea, endArea)
	var areasVisited int = 0
	for _, currNode := range path.Nodes {
		if currNode != nil {
			areasVisited = areasVisited + 1
		}
	}
	fmt.Printf("%d\n", areasVisited)
}
