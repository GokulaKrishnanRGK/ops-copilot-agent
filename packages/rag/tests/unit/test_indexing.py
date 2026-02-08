from opscopilot_rag.indexing import build_index_documents
from opscopilot_rag.types import Chunk, EmbeddingResult


def test_build_index_documents_maps_embeddings():
    chunks = [
        Chunk(document_id="doc", chunk_id="doc::chunk-0", index=0, text="a", metadata={"source": "doc"}),
        Chunk(document_id="doc", chunk_id="doc::chunk-1", index=1, text="b", metadata={"source": "doc"}),
    ]
    embeddings = EmbeddingResult(vectors=[[0.1], [0.2]], model_id="m", dimensions=1)
    documents = build_index_documents(chunks, embeddings)
    assert documents[0].chunk_id == "doc::chunk-0"
    assert documents[1].embedding == [0.2]


def test_build_index_documents_length_mismatch():
    chunks = [Chunk(document_id="doc", chunk_id="doc::chunk-0", index=0, text="a", metadata={})]
    embeddings = EmbeddingResult(vectors=[[0.1], [0.2]], model_id="m", dimensions=1)
    try:
        build_index_documents(chunks, embeddings)
    except ValueError as exc:
        assert "length mismatch" in str(exc)
    else:
        raise AssertionError("expected ValueError")
