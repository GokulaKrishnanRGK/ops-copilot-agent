package server

import (
	"encoding/json"
	"os"
	"regexp"
	"strconv"
)

func TruncateJSON(data any, maxBytes int) (any, bool) {
	if maxBytes <= 0 {
		return data, false
	}
	payload, err := json.Marshal(data)
	if err != nil {
		return data, false
	}
	if len(payload) <= maxBytes {
		return data, false
	}
	return map[string]any{
		"truncated":     true,
		"original_size": len(payload),
		"returned_size": maxBytes,
	}, true
}

var secretPattern = regexp.MustCompile(`(?i)(token|secret|password|apikey|api_key)`)

func RedactStrings(input any) any {
	switch v := input.(type) {
	case map[string]any:
		out := map[string]any{}
		for k, val := range v {
			if secretPattern.MatchString(k) {
				out[k] = "[REDACTED]"
				continue
			}
			out[k] = RedactStrings(val)
		}
		return out
	case []any:
		out := make([]any, 0, len(v))
		for _, item := range v {
			out = append(out, RedactStrings(item))
		}
		return out
	default:
		return v
	}
}

func MaxOutputBytes() int {
	value := os.Getenv("TOOL_MAX_OUTPUT_BYTES")
	if value == "" {
		return 0
	}
	n, err := strconv.Atoi(value)
	if err != nil {
		return 0
	}
	return n
}
