package internal

import "testing"

func TestSmoke(t *testing.T) {
	if true != true {
		t.Fatalf("unexpected")
	}
}
