package logging

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"go.opentelemetry.io/otel/trace"
)

var logger = slog.Default()

type ctxKey string

const (
	sessionIDKey  ctxKey = "session_id"
	agentRunIDKey ctxKey = "agent_run_id"
)

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

func resolveLevel() slog.Level {
	raw := strings.TrimSpace(os.Getenv("LOG_LEVEL"))
	if raw == "" {
		return slog.LevelInfo
	}
	var level slog.Level
	if err := level.UnmarshalText([]byte(strings.ToUpper(raw))); err != nil {
		return slog.LevelInfo
	}
	return level
}

func Configure() {
	logPath := os.Getenv("TOOL_SERVER_LOG_FILE")
	if logPath == "" {
		panic("TOOL_SERVER_LOG_FILE is required")
	}
	if err := os.MkdirAll(filepath.Dir(logPath), 0o755); err != nil {
		panic(fmt.Sprintf("failed to create log directory: %v", err))
	}

	rotatingFile, err := newDailyRotatingFile(logPath)
	if err != nil {
		panic(fmt.Sprintf("failed to initialize rotating log file: %v", err))
	}

	writer := io.MultiWriter(os.Stdout, rotatingFile)
	handler := slog.NewJSONHandler(writer, &slog.HandlerOptions{Level: resolveLevel()})
	logger = slog.New(handler).With("service", "tool-server", "component", "tool-server")
	slog.SetDefault(logger)
}

func WithRunContext(ctx context.Context, sessionID string, agentRunID string) context.Context {
	next := context.WithValue(ctx, sessionIDKey, sessionID)
	return context.WithValue(next, agentRunIDKey, agentRunID)
}

func Debug(ctx context.Context, message string, args ...any) {
	logWithContext(ctx, logger.DebugContext, message, args...)
}

func Info(ctx context.Context, message string, args ...any) {
	logWithContext(ctx, logger.InfoContext, message, args...)
}

func Error(ctx context.Context, message string, args ...any) {
	logWithContext(ctx, logger.ErrorContext, message, args...)
}

func logWithContext(
	ctx context.Context,
	write func(context.Context, string, ...any),
	message string,
	args ...any,
) {
	if ctx == nil {
		ctx = context.Background()
	}
	spanContext := trace.SpanContextFromContext(ctx)
	traceID := ""
	spanID := ""
	if spanContext.IsValid() {
		traceID = spanContext.TraceID().String()
		spanID = spanContext.SpanID().String()
	}
	sessionID, _ := ctx.Value(sessionIDKey).(string)
	agentRunID, _ := ctx.Value(agentRunIDKey).(string)
	attrs := []any{
		"trace_id", traceID,
		"span_id", spanID,
		"session_id", sessionID,
		"agent_run_id", agentRunID,
	}
	attrs = append(attrs, args...)
	write(ctx, message, attrs...)
}
