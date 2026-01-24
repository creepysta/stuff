package patterns

import (
	"fmt"
	"math/rand"
	"time"
)

/*
scenario: there are multiple sources of the same data being replicated in different servers
requirement: fire off the same query to all the instances and use the result from the first server
that responds

Output:
sam@debian:~/work/stuff/for-ref/go-concur-patterns (master) $ go run main.go
==============================
FanOut pattern
==============================
Going to need 84ms to respond...
Going to need 715ms to respond...
Going to need 549ms to respond...
Going to need 79ms to respond...
Going to need 235ms to respond...
{query: What's the wait time for your query?
result: 79}
==============================
*/

type Result struct {
	Result string
}

type Conn struct {
  DoQuery func(query string) Result
}

func FanOut(conns []Conn, query string) Result {
  ch := make(chan Result, len(conns))
  for _, conn := range conns {
    go func (c Conn) {
      ch <- c.DoQuery(query)
    }(conn)
  }
  return <- ch
}

func doQuery(query string) Result {
  dur := rand.Intn(1e3)
  fmt.Printf("Going to need %dms to respond...\n", dur)
  time.Sleep(time.Duration(dur)*time.Millisecond)
  return Result{ fmt.Sprintf("query: %s\nresult: %d", query, dur) }
}

func RunFanOut() {
  numConns := 5
  conns := make([]Conn, numConns)
  for i := 0; i < numConns; i++ {
    conns[i] = Conn{ doQuery }
  }
  fmt.Println(FanOut(conns, "What's the wait time for your query?"))
}
