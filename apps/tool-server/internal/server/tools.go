package server

type toolRequest struct {
	ToolName string         `json:"tool_name"`
	Args     map[string]any `json:"args"`
	Timeout  int            `json:"timeout_ms"`
}

type toolError struct {
	ErrorType string `json:"error_type"`
	Message   string `json:"message"`
	ToolName  string `json:"tool_name"`
	Duration  int    `json:"duration_ms"`
}

type toolResponse struct {
	ToolName  string     `json:"tool_name"`
	Status    string     `json:"status"`
	LatencyMS int        `json:"latency_ms"`
	Truncated bool       `json:"truncated"`
	Result    any        `json:"result"`
	Error     *toolError `json:"error"`
}
