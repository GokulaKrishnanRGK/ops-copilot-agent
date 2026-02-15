package main

import (
	"context"
	"net/http"
	"os"
	"time"

	"github.com/ops-copilot/tool-server/internal/logging"
	"github.com/ops-copilot/tool-server/internal/server"
)

func main() {
	logging.Configure()
	shutdownTelemetry, err := server.SetupTelemetry(context.Background())
	if err != nil {
		logging.Error(context.Background(), "telemetry init failed", "error", err)
		os.Exit(1)
	}
	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if shutdownErr := shutdownTelemetry(ctx); shutdownErr != nil {
			logging.Error(context.Background(), "telemetry shutdown failed", "error", shutdownErr)
		}
	}()

	addr := os.Getenv("TOOL_SERVER_ADDR")
	if addr == "" {
		addr = ":8080"
	}
	logging.Info(context.Background(), "tool server starting", "addr", addr)
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	if err := http.ListenAndServe(addr, mux); err != nil {
		logging.Error(context.Background(), "http server failed", "addr", addr, "error", err)
		os.Exit(1)
	}
}
