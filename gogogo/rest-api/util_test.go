package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestGetAll(t *testing.T) {
  resp, err := http.Get("http://0.0.0.0:80/albums")
  if err != nil {
    log.Fatal(err)
  }
  fmt.Print(resp.Status, resp.StatusCode)
  body, err := ioutil.ReadAll(resp.Body)
  if err != nil {
    log.Fatal(err)
  }
  log.Printf(string(body))
  assert.Equal(t, 200, resp.StatusCode, "Successful get should return 200")
}

func TestGetByIdPass(t *testing.T) {
  assert := assert.New(t)
  for id := 1; id <= 3; id++ {
    log.Printf("Trying random id: %v", id)
    endpoint := fmt.Sprintf("http://0.0.0.0:80/albums/%v", id)
    resp, err := http.Get(endpoint)
    if err != nil {
      log.Fatal(err)
    }
    fmt.Print(resp.Status, resp.StatusCode)
    body, err := ioutil.ReadAll(resp.Body)
    if err != nil {
      log.Fatal(err)
    }
    log.Printf(string(body))
    assert.Equal(200, resp.StatusCode, "Successful get should return 200")
  }
}

func TestGetByIdFail(t *testing.T) {
  id := 999
  log.Printf("Trying random id: %v", id)
  endpoint := fmt.Sprintf("http://0.0.0.0:80/albums/%v", id)
  resp, err := http.Get(endpoint)
  if err != nil {
    log.Fatal(err)
  }
  fmt.Print(resp.Status, resp.StatusCode)
  body, err := ioutil.ReadAll(resp.Body)
  if err != nil {
    log.Fatal(err)
  }
  log.Printf(string(body))
  assert.Equal(t, 404, resp.StatusCode, "Fail get should return 404")
}

func TestPost(t *testing.T) {
  assert := assert.New(t)
  for i := 0; i < 10; i++ {
    newAlbum := map[string] any {
      "ID"     : fmt.Sprint(i),
      "Title"  : fmt.Sprintf("Test Title %v", i),
      "Artist" : fmt.Sprintf("Test Artist %v", i),
      "Price"  : float64(i * 10) + 0.99,
    }
    postBody, _ := json.Marshal(newAlbum)
    resBody := bytes.NewBuffer(postBody)
    resp, err := http.Post("http://0.0.0.0:80/albums", "application/json", resBody)
    if err != nil {
      log.Fatalf("An error occurred for POST: %v", err)
    }
    defer resp.Body.Close()
    body, err := ioutil.ReadAll(resp.Body)
    if err != nil {
      log.Fatalln(err)
    }
    sb := string(body)
    log.Printf(sb)
    assert.Equal(201, resp.StatusCode, "Successful post creation should return 201")
  }
}
