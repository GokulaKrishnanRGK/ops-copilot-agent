package main

import (
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type linePrefixWriter struct {
	mu       sync.Mutex
	writer   io.Writer
	buffered string
}

type dailyRotatingFile struct {
	mu         sync.Mutex
	path       string
	file       *os.File
	currentDay string
}

func newDailyRotatingFile(path string) (*dailyRotatingFile, error) {
	r := &dailyRotatingFile{path: path}
	if err := r.openForToday(); err != nil {
		return nil, err
	}
	return r, nil
}

func (r *dailyRotatingFile) Write(p []byte) (int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if err := r.rotateIfNeeded(); err != nil {
		return 0, err
	}
	return r.file.Write(p)
}

func (r *dailyRotatingFile) rotateIfNeeded() error {
	today := time.Now().Local().Format("2006-01-02")
	if r.file != nil && r.currentDay == today {
		return nil
	}
	if r.file != nil {
		if err := r.file.Close(); err != nil {
			return err
		}
		r.file = nil
		rotated := fmt.Sprintf("%s.%s", r.path, r.currentDay)
		if err := safeRename(r.path, rotated); err != nil {
			return err
		}
	}
	return r.openForToday()
}

func (r *dailyRotatingFile) openForToday() error {
	now := time.Now().Local()
	today := now.Format("2006-01-02")
	if err := rotateStaleBaseFile(r.path, today, now.Location()); err != nil {
		return err
	}
	file, err := os.OpenFile(r.path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	r.file = file
	r.currentDay = today
	return nil
}

func rotateStaleBaseFile(path string, today string, loc *time.Location) error {
	info, err := os.Stat(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	fileDay := info.ModTime().In(loc).Format("2006-01-02")
	if fileDay == today {
		return nil
	}
	return safeRename(path, fmt.Sprintf("%s.%s", path, fileDay))
}

func safeRename(src string, dst string) error {
	if _, err := os.Stat(src); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	target := dst
	if _, err := os.Stat(target); err == nil {
		target = fmt.Sprintf("%s-%s", dst, time.Now().Local().Format("150405"))
	}
	return os.Rename(src, target)
}

func (w *linePrefixWriter) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	w.buffered += string(p)
	lines := strings.Split(w.buffered, "\n")
	w.buffered = lines[len(lines)-1]
	for i := 0; i < len(lines)-1; i++ {
		line := lines[i]
		if err := w.writeLine(line); err != nil {
			return 0, err
		}
	}
	return len(p), nil
}

func (w *linePrefixWriter) writeLine(line string) error {
	ts := time.Now().Local().Format("2006-01-02T15:04:05-0700")
	prefix := fmt.Sprintf("ts=%s service=tool-server thread_id=%d ", ts, currentThreadID())
	_, err := io.WriteString(w.writer, prefix+line+"\n")
	return err
}

func configureLogging() {
	logPath := os.Getenv("TOOL_SERVER_LOG_FILE")
	if logPath == "" {
		log.Fatal("TOOL_SERVER_LOG_FILE is required")
	}
	if err := os.MkdirAll(filepath.Dir(logPath), 0o755); err != nil {
		log.Fatalf("failed to create log directory: %v", err)
	}

	rotatingFile, err := newDailyRotatingFile(logPath)
	if err != nil {
		log.Fatalf("failed to initialize rotating log file: %v", err)
	}

	multi := io.MultiWriter(os.Stdout, rotatingFile)
	log.SetFlags(0)
	log.SetOutput(&linePrefixWriter{writer: multi})
	log.SetPrefix("")
}
