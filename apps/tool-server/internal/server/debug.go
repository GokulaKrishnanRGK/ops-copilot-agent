package server

import (
	"log"
	"os"
)

func debugEnabled() bool {
	return os.Getenv("TOOL_SERVER_DEBUG") == "1"
}

func debugLogf(format string, args ...any) {
	if !debugEnabled() {
		return
	}
	log.Printf(format, args...)
}
