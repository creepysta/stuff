package patterns

import "fmt"

/*
  U1 -+
      +- Output
  U2 -+
*/
func FanIn2(in1, in2 chan string) chan string {
  out := make(chan string)
  go func() { for { out <- <-in1 }}()
  go func() { for { out <- <-in2 }}()
  return out
}

func FanInSelect(in1, in2 chan string) chan string {
  out := make(chan string)
  // single go routine with select
  go func() {
    for {
      select {
        case s:= <- in1: out <- s
        case s:= <- in2: out <- s
      }
    }
  }()
  return out
}

func FanIn(ins ...chan string) chan string {
  out := make(chan string)
  for _, inp := range ins {
    go func(inp chan string) {
      for got := range inp {
        out <- got
      }
    }(inp)
  }
  return out
}

func RunFanIn() {
  c := FanIn(Generator("Alice"), Generator("Bob"), Generator("Janice"))
  for i := 0; i < 15; i++ {
    got := <- c
    fmt.Printf("Got message: %s\n", got)
  }
}
