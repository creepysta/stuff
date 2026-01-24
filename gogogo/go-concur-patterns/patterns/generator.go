package patterns

/*
  Generator: function that returns a channel
*/

import (
	"fmt"
	"math/rand"
	"time"
)

func Generator(name string) chan string {
  c := make(chan string)
  go func() {
    for {
      c <- fmt.Sprintf("Hi %s", name)
      time.Sleep(time.Duration(rand.Intn(1e3))*time.Millisecond)
    }
  }()
  return c
}

func RunGenerator() {
  alice := Generator("Alice")
  bob := Generator("Bob")
  for i := 0; i < 5; i++ {
    messageAlice := <- alice
    messageBob := <- bob
    fmt.Printf("Alice said: %s\n", messageAlice)
    fmt.Printf("Bob said: %s\n", messageBob)
  }
}

func RunGeneratorWithSelect() { // fan in example is a more generic case for this
  alice := Generator("Alice")
  bob := Generator("Bob")
  for i := 0; i < 10; i++ {
    select {
    case messageAlice := <- alice:
      fmt.Printf("Alice said: %s\n", messageAlice)
    case messageBob := <- bob:
      fmt.Printf("Bob said: %s\n", messageBob)
    case <- time.After(500 * time.Millisecond): // timing out each message. in case you want to timeout the whole loop, declare the time.After outside the loop
      fmt.Println("Timed out waiting for message...")
    // default: // doesn't block anymore, so the non default cases may never trigger ...
    //   fmt.Println("Neither channel was called")
    }
  }
}
