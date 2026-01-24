package patterns

import (
	"fmt"
	"math/rand"
	"time"
)


var (
  Web = fakeSearch("web")
  Image = fakeSearch("image")
  Video = fakeSearch("video")
)

type SearchResult string

type Search func(query string) SearchResult

func fakeSearch(kind string) Search {
  return func(query string) SearchResult {
    time.Sleep(time.Duration(rand.Intn(100)) * time.Millisecond)
    return SearchResult(fmt.Sprintf("%s result for %q\n", kind, query))
  }
}

/*
worst case scenario they will take 300 seconds to finish altogether
[web result for "golang"
 image result for "golang"
 video result for "golang"
]
250.276948ms
*/

func GoogleSlow(query string) (results []SearchResult) {
  // results := make([]SearchResult, 0) // already defined in return type
  results = append(results, Web(query))
  results = append(results, Image(query))
  results = append(results, Video(query))
  return results
}

/*
[image result for "golang"
 web result for "golang"
 video result for "golang"
]
85.634148ms
*/
func GoogleGoRoutines(query string) (results []SearchResult) {
  // results := make([]SearchResult, 0) // already defined in return type
  c := make(chan SearchResult)
  go func() { c <- Web(query) }()
  go func() { c <- Image(query) }()
  go func() { c <- Video(query) }()
  // for result := range c {
  for i := 0; i < 3; i++ {
    result := <- c
    results = append(results, result)
  }
  return results
}

/*
==== dummy google search (slow)
[web result for "golang"
 image result for "golang"
 video result for "golang"
]
142.876507ms
==== dummy google search (go routines)
[image result for "golang"
 web result for "golang"
 video result for "golang"
]
65.858791ms
==== dummy google search (go routines with total timeout)
Timed out
[web result for "golang"
]
80.842928ms
*/
func GoogleGoRoutinesTimeout(query string) (results []SearchResult) {
  // results := make([]SearchResult, 0) // already defined in return type
  c := make(chan SearchResult)
  go func() { c <- Web(query) }()
  go func() { c <- Image(query) }()
  go func() { c <- Video(query) }()
  // for result := range c {
  timeout := time.After(80 * time.Millisecond)
  for i := 0; i < 3; i++ {
    select {
    case result := <- c:
      results = append(results, result)
    case <-timeout:
      fmt.Println("Timed out")
      return
    }
  }
  return results
}

/*
==== dummy google search (slow)
[web result for "golang"
 image result for "golang"
 video result for "golang"
]
103.74642ms
==== dummy google search (go routines)
[video result for "golang"
 web result for "golang"
 image result for "golang"
]
76.687044ms
==== dummy google search (go routines with total timeout)
Timed out
[web result for "golang"
 image result for "golang"
]
82.530165ms
==== dummy google search (go routines return first response from all replicas)
[video: replica 4 result for "golang"
 web: replica 1 result for "golang"
 image: replica 1 result for "golang"
]
36.091345ms
==============================
*/
func First(query string, replicas ...Search) SearchResult {
  c := make(chan SearchResult)
  searchReplica := func(i int) { c <- replicas[i](query)  }
  for i := range replicas {
    go searchReplica(i)
  }
  return <- c
}

func GoogleGoRoutinesFirstSimple(query string) (results []SearchResult) {
  Web1, Web2 := fakeSearch("web: replica 1"), fakeSearch("web: replica 2")
  Video1, Video2 := fakeSearch("video: replica 1"), fakeSearch("video: replica 2")
  Image1, Image2 := fakeSearch("image: replica 1"), fakeSearch("image: replica 2")
  c := make(chan SearchResult)
  go func() { c <- First(query, Web1, Web2) } ()
  go func() { c <- First(query, Image1, Image2) } ()
  go func() { c <- First(query, Video1, Video2) } ()
  timeout := time.After(80 * time.Millisecond)
  for i := 0; i < 3; i++ {
    select {
    case result := <- c:
      results = append(results, result)
    case <-timeout:
      fmt.Println("timed out")
      return
    }
  }
  return results
}

func GoogleGoRoutinesFirstGeneric(query string) (results []SearchResult) {
  Web1, Web2, Web3 := fakeSearch("web: replica 1"), fakeSearch("web: replica 2"), fakeSearch("web: replica 3")
  Video1, Video2, Video3, Video4 := fakeSearch("video: replica 1"), fakeSearch("video: replica 2"), fakeSearch("video: replica 3"), fakeSearch("video: replica 4")
  Image1, Image2 := fakeSearch("image: replica 1"), fakeSearch("image: replica 2")
  webRepls := []Search{ Web1, Web2, Web3 }
  videoRepls := []Search{ Video1, Video2, Video3, Video4 }
  imageRepls := []Search{ Image1, Image2 }
  c := make(chan SearchResult)

  queryFn := func (search []Search) { c <- First(query, search...) }
  for _, repl := range [][]Search{webRepls, videoRepls, imageRepls} {
    go queryFn(repl)
  }
  // range over a channel blocks indefinitely (even after collecting all results)
  // if you know how many results you need, have a fixed for loop, or use sync.WaitGroup
  // for _, result := range c {
  timeout := time.After(80 * time.Millisecond)
  for i := 0; i < 3; i++ {
    select {
    case result := <- c:
      results = append(results, result)
    case <-timeout:
      fmt.Println("timed out")
      return
    }
  }
  return results
}

func RunGoogle(query string, google func(query string) []SearchResult) {
  start := time.Now()
  results := google(query)
  elapsed := time.Since(start)
  fmt.Println(results)
  fmt.Println(elapsed)
}
