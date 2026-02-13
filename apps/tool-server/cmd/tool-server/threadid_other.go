//go:build !linux

package main

import "os"

func currentThreadID() int {
	return os.Getpid()
}
