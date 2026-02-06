from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    document_id: str
    source_path: str
    content: str
    metadata: dict


@dataclass(frozen=True)
class Chunk:
    document_id: str
    chunk_id: str
    index: int
    text: str
    metadata: dict


@dataclass(frozen=True)
class EmbeddingRequest:
    texts: list[str]


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]
    model_id: str
    dimensions: int


@dataclass(frozen=True)
class OpenSearchConfig:
    url: str
    index: str
    username: str | None = None
    password: str | None = None
    verify_certs: bool = False


@dataclass(frozen=True)
class IndexedChunk:
    document_id: str
    chunk_id: str
    chunk_index: int
    source: str
    text: str
    metadata: dict
    embedding: list[float]


@dataclass(frozen=True)
class RetrievalResult:
    document_id: str
    chunk_id: str
    chunk_index: int
    source: str
    text: str
    metadata: dict
    score: float


@dataclass(frozen=True)
class Citation:
    document_id: str
    chunk_id: str
    source: str
    score: float
    metadata: dict
