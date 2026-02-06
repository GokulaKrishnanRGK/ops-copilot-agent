package k8s

import "strings"

func ParseAllowlist(raw string) map[string]struct{} {
	allowed := map[string]struct{}{}
	for _, item := range strings.Split(raw, ",") {
		name := strings.TrimSpace(item)
		if name == "" {
			continue
		}
		allowed[name] = struct{}{}
	}
	return allowed
}

func IsAllowed(allowed map[string]struct{}, namespace string) bool {
	if len(allowed) == 0 {
		return false
	}
	_, ok := allowed[namespace]
	return ok
}
