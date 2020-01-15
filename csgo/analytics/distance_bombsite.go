package main

import (
	"fmt"
	"flag"
	"os"
	"github.com/mrazza/gonav"
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

	current_map := *navPathPtr
	start_x := *startXPtr
	start_y := *startYPtr
	start_z := *startZPtr
	bombsite := *bombsitePtr

	// Read in args
	//current_map, start_x, start_y, start_z, end_x, end_y, end_z = DemoPathFromArgs()
	// Read in parser
	f_nav, _ := os.Open("../../data/original_nav_files/" + current_map + ".nav")
	parser_nav := gonav.Parser{Reader: f_nav}
	mesh, _ := parser_nav.Parse()
	start_location := gonav.Vector3{X: float32(start_x), Y: float32(start_y), Z: float32(start_z)}
	end_location := gonav.Vector3{X: float32(end_x), Y: float32(end_y), Z: float32(end_z)}
	start_area := mesh.GetNearestArea(start_location, true)

	if bombsite == "A" {
		bombsite_mesh := mesh.GetPlaceByName("BombsiteA")
		bombsite_center, _ := bombsite_mesh.GetEstimatedCenter()
		bombsite_area := mesh.GetNearestArea(bombsite_center, false)
	} else {
		bombsite_mesh := mesh.GetPlaceByName("BombsiteB")
		bombsite_center, _ := bombsite_mesh.GetEstimatedCenter()
		bombsite_area := mesh.GetNearestArea(bombsite_center, false)
	}

	path, _ := gonav.SimpleBuildShortestPath(start_area, bombsite_area)
	var areas_visited int = 0
	for _, currNode := range path.Nodes {
		if currNode != nil {
			areas_visited = areas_visited + 1
		}
	}
	fmt.Printf("%d\n", areas_visited)
}
