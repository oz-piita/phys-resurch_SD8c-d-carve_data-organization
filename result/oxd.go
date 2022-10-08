package main

import (
	"encoding/csv"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"strconv"
)

// a follow-up calculation of oxidation degrees.
func main() {
	files, _ := ioutil.ReadDir("./")
	for _, f := range files {
		if f.Name() == "edit_history.csv" || f.Name() == "desktop.ini" || f.Name() == "oxd.go" || f.Name() == "充放電.SMP" {
			continue
		}
		filename := f.Name()
		fmt.Println(filename)

		file, err := os.Open(filename)
		if err != nil {
			log.Fatal(err)
		}
		defer file.Close()

		r := csv.NewReader(file)
		rows, err := r.ReadAll()
		if err != nil {
			log.Fatal(err)
		}

		// [][]string Loop
		oxd, cap := 0.0, 0.0
		for _, v := range rows {
			if v[0] != "" {
				i, _ := strconv.ParseFloat(v[0], 64)
				if oxd < i {
					oxd = i
				}
			}
			if v[2] != "" {
				j, _ := strconv.ParseFloat(v[2], 64)
				if cap < j {
					cap = j
				}
			}
		}
		fmt.Println(1 - oxd/cap)
	}
}
