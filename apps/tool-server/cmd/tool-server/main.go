package main

import (
	"log"
	"net/http"
	"os"

	"github.com/ops-copilot/tool-server/internal/server"
)

func main() {
	addr := os.Getenv("TOOL_SERVER_ADDR")
	if addr == "" {
		addr = ":8080"
	}
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	log.Fatal(http.ListenAndServe(addr, mux))
}
