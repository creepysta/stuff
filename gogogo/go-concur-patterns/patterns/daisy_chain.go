package patterns

import "fmt"

/*
   U9 < U8 < U7 < U6 < U5 < U4 < U3 < U2 < U1
*/

func f(left, right chan int) {
  left <- 1 + <- right
}

func RunDaisyChain() {
  const n = 100_000
  leftmost := make(chan int)
  right := leftmost
  left := leftmost
  for i := 0; i < n; i++ {
    right = make(chan int)
    go f(left, right)
    left = right
  }
  go func (c chan int) { c <- 1 } (right)
  fmt.Printf("leftmost: %d\n", <-leftmost)
}
