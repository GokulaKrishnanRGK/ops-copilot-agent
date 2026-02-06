package main

import (
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/joho/godotenv"
	"github.com/ops-copilot/tool-server/internal/server"
)

func main() {
	root, err := repoRoot()
	if err == nil {
		envPath := filepath.Join(root, ".env")
		_ = godotenv.Load(envPath)
	}
	addr := os.Getenv("TOOL_SERVER_ADDR")
	if addr == "" {
		addr = ":8080"
	}
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	log.Fatal(http.ListenAndServe(addr, mux))
}

func repoRoot() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	return filepath.Clean(filepath.Join(cwd, "..", "..", "..")), nil
}
