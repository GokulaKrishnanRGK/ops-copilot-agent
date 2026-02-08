package tests

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestRepoRoot(t *testing.T) {
	require := require.New(t)
	root, err := repoRoot()
	require.NoError(err)
	require.NotEmpty(root)
}

func repoRoot() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	path := filepath.Clean(filepath.Join(cwd, "..", "..", ".."))
	return path, nil
}
