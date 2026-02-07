package tests

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/joho/godotenv"
	"github.com/stretchr/testify/require"
)

func TestMain(m *testing.M) {
	root, err := repoRoot()
	if err == nil {
		_ = godotenv.Load(filepath.Join(root, ".env"))
	}
	exit := m.Run()
	os.Exit(exit)
}

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
