package main

import (
	"flag"
	"fmt"
	"os"

	metadata "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/metadata"
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

	mapName := *MapPtr
	x := *XPtr
	y := *YPtr

	// Get metadata for the map that the game was played on for coordinate translations
	mapMetadata := metadata.MapNameToMap[mapName]

	newX, newY := mapMetadata.TranslateScale(x, y)

	fmt.Println(newX)
	fmt.Println(newY)
}

func checkError(err error) {
	if err != nil {
		panic(err)
	}
}
