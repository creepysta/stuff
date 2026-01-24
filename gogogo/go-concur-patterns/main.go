package main

import (
	"fmt"

	"github.com/creepysta/concurrency-patterns/advanced"
	"github.com/creepysta/concurrency-patterns/patterns"
)

func RunPatterns() {
	fmt.Println("==============================")
	fmt.Println("Generator pattern")
	fmt.Println("==============================")
	patterns.RunGenerator()
	fmt.Println("==============================")

	fmt.Println("==============================")
	fmt.Println("Generator pattern with 'select'")
	fmt.Println("==============================")
	patterns.RunGeneratorWithSelect()
	fmt.Println("==============================")

	fmt.Println("==============================")
	fmt.Println("FanIn pattern")
	fmt.Println("==============================")
	patterns.RunFanIn()
	fmt.Println("==============================")

	fmt.Println("==============================")
	fmt.Println("FanOut pattern")
	fmt.Println("==============================")
	patterns.RunFanOut()
	fmt.Println("==============================")

	fmt.Println("==============================")
	fmt.Println("Daisy Chain pattern")
	fmt.Println("==============================")
	patterns.RunDaisyChain()
	fmt.Println("==============================")

	fmt.Println("==============================")
	fmt.Println("==== dummy google search (slow)")
	patterns.RunGoogle("golang", patterns.GoogleSlow)
	fmt.Println("==== dummy google search (go routines)")
	patterns.RunGoogle("golang", patterns.GoogleGoRoutines)
	fmt.Println("==== dummy google search (go routines with total timeout)")
	patterns.RunGoogle("golang", patterns.GoogleGoRoutinesTimeout)
	fmt.Println("==== dummy google search (go routines return first response from all replicas)")
	patterns.RunGoogle("golang", patterns.GoogleGoRoutinesFirstSimple)
	fmt.Println("==============================")
}

func RunAdvanced() {
	fmt.Println("==============================")
	fmt.Println("Ping Pong")
	fmt.Println("==============================")
  advanced.RunPingPong()
	fmt.Println("==============================")
}

func main() {
  //RunPatterns()
  RunAdvanced()
}
