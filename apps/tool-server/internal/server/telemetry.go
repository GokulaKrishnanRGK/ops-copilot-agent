package server

import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
)

func startToolSpan(ctx context.Context, toolName string) (context.Context, func(attrs map[string]any)) {
	tracer := otel.Tracer("tool-server")
	ctx, span := tracer.Start(ctx, "tool.call")
	end := func(attrs map[string]any) {
		span.SetAttributes(AttributesFromMap(attrs)...)
		span.End()
	}
	span.SetAttributes(attribute.String("tool_name", toolName))
	return ctx, end
}

func AttributesFromMap(attrs map[string]any) []attribute.KeyValue {
	out := make([]attribute.KeyValue, 0, len(attrs))
	for k, v := range attrs {
		switch t := v.(type) {
		case string:
			out = append(out, attribute.String(k, t))
		case bool:
			out = append(out, attribute.Bool(k, t))
		case int:
			out = append(out, attribute.Int(k, t))
		case int64:
			out = append(out, attribute.Int64(k, t))
		case float64:
			out = append(out, attribute.Float64(k, t))
		}
	}
	return out
}
