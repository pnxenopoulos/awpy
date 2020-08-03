package main

import (
	"flag"
	"fmt"
	"os"

	gonav "github.com/pnxenopoulos/csgonavparse"
)

func main() {
	fl := new(flag.FlagSet)

	MapPtr := fl.String("map", "", "Map name `path`")
	XPtr := fl.Float64("x", 0, "X")
	YPtr := fl.Float64("y", 0, "Y")
	ZPtr := fl.Float64("z", 0, "Z")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	mapName := *MapPtr
	x := *XPtr
	y := *YPtr
	z := *ZPtr

	fNav, _ := os.Open("../data/nav/" + mapName + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()

	Loc := gonav.Vector3{X: float32(x), Y: float32(y), Z: float32(z)}
	Area := mesh.GetNearestArea(Loc, true)

	if Area != nil {
		fmt.Println(Area)
	} else {
		fmt.Println("Error")
	}
}

func checkError(err error) {
	if err != nil {
		panic(err)
	}
}
