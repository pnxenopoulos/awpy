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
	bombsitePtr := fl.String("bombsite", "A", "A or B")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	currentMap := *navPathPtr
	startX := *startXPtr
	startY := *startYPtr
	startZ := *startZPtr
	bombsite := *bombsitePtr

	// Read in args
	//currentMap, startX, startY, startZ, end_x, end_y, end_z = DemoPathFromArgs()
	// Read in parser
	fNav, _ := os.Open("../data/nav/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()
	startLoc := gonav.Vector3{X: float32(startX), Y: float32(startY), Z: float32(startZ)}
	startArea := mesh.GetNearestArea(startLoc, true)

	bombsiteMesh := mesh.GetPlaceByName("BombsiteA")
	bombsiteCenter, _ := bombsiteMesh.GetEstimatedCenter()
	bombsitArea := mesh.GetNearestArea(bombsiteCenter, false)
	if bombsite == "B" {
		bombsiteMesh = mesh.GetPlaceByName("BombsiteB")
		bombsiteCenter, _ = bombsiteMesh.GetEstimatedCenter()
		bombsitArea = mesh.GetNearestArea(bombsiteCenter, false)
	}

	path, _ := gonav.SimpleBuildShortestPath(startArea, bombsitArea)
	var areasVisited int = 0
	for _, currNode := range path.Nodes {
		if currNode != nil {
			areasVisited = areasVisited + 1
		}
	}
	fmt.Printf("%d", areasVisited)
}
