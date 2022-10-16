package main

import (
	"github.com/gin-gonic/gin"
)

func main() {
    router := gin.Default()
    router.GET("/albums", getAlbums)
    router.GET("/albums/:id", getAlbumByID)
    router.POST("/albums", postAlbums)

    router.Run("0.0.0.0:80")
}
