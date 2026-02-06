from __future__ import annotations

from pathlib import Path

from .types import Document


def normalize_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    normalized_lines: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and previous_blank:
            continue
        normalized_lines.append(line)
        previous_blank = is_blank
    return "\n".join(normalized_lines).strip()


def _allowed_extension(path: Path, extensions: set[str] | None) -> bool:
    if extensions is None:
        return True
    return path.suffix.lower() in extensions


def discover_document_paths(root_dir: Path, extensions: set[str] | None) -> list[Path]:
    root = root_dir.resolve()
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _allowed_extension(path, extensions):
            paths.append(path)
    return sorted(paths)


def load_documents(
    root_dir: str | Path,
    extensions: list[str] | None = None,
    encoding: str = "utf-8",
) -> list[Document]:
    root = Path(root_dir).resolve()
    extension_set = {ext.lower() for ext in extensions} if extensions else None
    documents: list[Document] = []
    for path in discover_document_paths(root, extension_set):
        raw = path.read_text(encoding=encoding)
        content = normalize_text(raw)
        relative_path = path.relative_to(root).as_posix()
        documents.append(
            Document(
                document_id=relative_path,
                source_path=str(path),
                content=content,
                metadata={"source": relative_path},
            )
        )
    return documents
