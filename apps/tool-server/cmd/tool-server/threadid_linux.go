//go:build linux

package main

import "syscall"

func currentThreadID() int {
	return syscall.Gettid()
}
