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
	endXPtr := fl.Float64("end_x", 0, "End X")
	endYPtr := fl.Float64("end_y", 0, "End Y")
	endZPtr := fl.Float64("end_z", 0, "End Z")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	current_map := *navPathPtr
	start_x := *startXPtr
	start_y := *startYPtr
	start_z := *startZPtr
	end_x := *endXPtr
	end_y := *endYPtr
	end_z := *endZPtr
	// Read in args
	//current_map, start_x, start_y, start_z, end_x, end_y, end_z = DemoPathFromArgs()
	// Read in parser
	f_nav, _ := os.Open("../data/original_nav_files/" + current_map + ".nav")
	parser_nav := gonav.Parser{Reader: f_nav}
	mesh, _ := parser_nav.Parse()
	start_location := gonav.Vector3{X: float32(start_x), Y: float32(start_y), Z: float32(start_z)}
	end_location := gonav.Vector3{X: float32(end_x), Y: float32(end_y), Z: float32(end_z)}
	start_area := mesh.GetNearestArea(start_location, false)
	end_area := mesh.GetNearestArea(end_location, false)
	path, _ := gonav.SimpleBuildShortestPath(start_area, end_area)
	var areas_visited int = 0
	for _, currNode := range path.Nodes {
		if currNode != nil {
			areas_visited = areas_visited + 1
		}
	}
	fmt.Printf("%d\n", areas_visited)
}
