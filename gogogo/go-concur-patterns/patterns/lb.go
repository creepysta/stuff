package patterns

/**
ref: https://youtu.be/jgVhBThJdXc?t=1676

idea here is we want to allocate the work coming in from the requesters to
the least loaded worker


requesters:     r1 r2 r3 r4 .... rn ------+
                \  \  |  / ....  /        |
                      v                   |
load balancer: +----------------------+   |
               |     balancer         |   |
               +----------------------+   ^
                |  |  |  ...... |         |
workers:        w1 w2 w3 ...... wn -------+
**/

import (
	"container/heap"
	"fmt"
	"math/rand"
	"time"
)

// ------ REQUESTER -------

type Request struct {
  fn func() int
  c  chan int
}

func workFn() int {
  fmt.Printf("Working ...")
  return 0
}

func processResult(result int) {
  fmt.Printf("Processing result... %d", result)
}

func requester(work chan Request) {
  c := make(chan int)
  for {
    time.Sleep(time.Duration(rand.Float32()*10)*time.Second)
    work <- Request{workFn, c}
    result := <- c
    processResult(result)
  }
}


// ------ LOAD BALANCER -------
type Pool []*Worker
type Balancer struct {
  pool Pool
  done chan *Worker
}

func (b *Balancer) balance(work chan Request) {
  for {
    select {
    case req := <- work: // recieved a request
      b.dispatch(req)    // send it to a worker
    case w := <- b.done: // a worker has finished a request
      b.completed(w)     // update its info
    }
  }
}

// How do we implement dispatch
// Let's use a heap to choose the most lightly loaded worker by attaching the necessary methods to type Pool
// ---------------- heap --------------
func (p Pool) Len() int {
  return len(p)
}

func (p *Pool) Push(x any) {
  *p = append(*p, x.(*Worker))
}

func (p *Pool) Pop() any {
  old := *p
  n := len(*p)
  x := old[n-1]
  *p = old[0 : n-1]
  return x
}

func (p Pool) Swap(i, j int) {
  p[i], p[j] = p[j], p[i]
  // p[p[i].index], p[p[j].index] = p[p[j].index], p[p[i].index]
}

func (p Pool) Less(i, j int) bool {
  return p[i].pending < p[j].pending
}
// ------------------------------------

// Send requests to workers
func (b *Balancer) dispatch (req Request) {
  w := heap.Pop(&b.pool).(*Worker) // get the least loaded worker
  w.requests <- req                // ... assign a task
  w.pending++                      // add one more in its queue
  heap.Push(&b.pool, w)            // put it back in the loop
}

// Job is complete; update heap
func (b *Balancer) completed (w *Worker) {
  w.pending --                  // one fewer in its queue
  heap.Remove(&b.pool, w.index) // remove it from heap
  heap.Push(&b.pool, w)         // put it back where it belongs
}


// ------ WORKER -------
type Worker struct {
  requests chan Request
  pending int
  index int
}

func (w *Worker) work (done chan *Worker) {
  for {
    req := <- w.requests // get the request from load balancer
    req.c <- req.fn()    // call fn and send result
    done <- w            // we've finished processing the request
  }
}
