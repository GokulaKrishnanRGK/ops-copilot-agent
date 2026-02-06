package server

import "net/http"

func MapError(tool string, errType string, message string) *toolError {
	return &toolError{
		ErrorType: errType,
		Message:   message,
		ToolName:  tool,
		Duration:  0,
	}
}

func StatusForError(err *toolError) int {
	if err == nil {
		return http.StatusOK
	}
	switch err.ErrorType {
	case "invalid_input":
		return http.StatusBadRequest
	case "permission_denied":
		return http.StatusForbidden
	case "timeout":
		return http.StatusRequestTimeout
	case "not_found":
		return http.StatusNotFound
	default:
		return http.StatusInternalServerError
	}
}
