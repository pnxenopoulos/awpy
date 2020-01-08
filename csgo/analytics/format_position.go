package main

import (
	"fmt"
	"os"
	"flag"

	metadata "github.com/markus-wa/demoinfocs-golang/metadata"
)

func main() {
	//
	// Parsing
	//

	fl := new(flag.FlagSet)

	MapPtr := fl.String("map", "", "Map name `path`")
	XPtr := fl.Float64("x", 0, "X")
	YPtr := fl.Float64("y", 0, "Y")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	map_name := *MapPtr
	x := *XPtr
	y := *YPtr

	// Get metadata for the map that the game was played on for coordinate translations
	mapMetadata := metadata.MapNameToMap[map_name]

	new_x, new_y := mapMetadata.TranslateScale(x, y)

	fmt.Println(new_x)
	fmt.Println(new_y)
}

func checkError(err error) {
	if err != nil {
		panic(err)
	}
}
