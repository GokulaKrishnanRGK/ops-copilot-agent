from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Iterable

from opscopilot_rag.chunking import chunk_text
from opscopilot_rag.embeddings import OpenAIEmbeddingAdapter
from opscopilot_rag.indexing import build_index_documents, bulk_upsert_chunks
from opscopilot_rag.ingestion import load_documents
from opscopilot_rag.opensearch_client import OpenSearchClient
from opscopilot_rag.types import EmbeddingRequest, EmbeddingResult, OpenSearchConfig

logger = logging.getLogger(__name__)


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _iter_batches(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest documents into OpenSearch for RAG retrieval."
    )
    parser.add_argument("--root", required=True, help="Root directory to ingest")
    parser.add_argument(
        "--extensions",
        help="Comma-separated list of allowed file extensions (e.g. .md,.txt)",
    )
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--opensearch-url")
    parser.add_argument("--opensearch-index")
    parser.add_argument("--opensearch-username")
    parser.add_argument("--opensearch-password")
    parser.add_argument(
        "--opensearch-verify-certs",
        default=os.getenv("OPENSEARCH_VERIFY_CERTS", "false"),
    )
    return parser


def ingest_documents(args: argparse.Namespace) -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    extensions = None
    if args.extensions:
        extensions = [ext.strip() for ext in args.extensions.split(",") if ext.strip()]

    logger.debug("ingest: root=%s", args.root)
    logger.debug("ingest: extensions=%s", extensions)
    documents = load_documents(args.root, extensions=extensions)
    if not documents:
        print("No documents found to ingest.")
        return 1
    logger.debug("ingest: documents=%d", len(documents))

    chunks = []
    for doc in documents:
        chunks.extend(
            chunk_text(
                doc.document_id,
                doc.content,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                metadata=doc.metadata,
            )
        )

    if not chunks:
        print("No chunks created from documents.")
        return 1
    logger.debug("ingest: chunks=%d", len(chunks))

    if args.opensearch_url and args.opensearch_index:
        config = OpenSearchConfig(
            url=args.opensearch_url,
            index=args.opensearch_index,
            username=args.opensearch_username,
            password=args.opensearch_password,
            verify_certs=_parse_bool(args.opensearch_verify_certs),
        )
    else:
        config = None
    os_client = OpenSearchClient(config)

    adapter = OpenAIEmbeddingAdapter()
    texts = [chunk.text for chunk in chunks]
    vectors: list[list[float]] = []
    dimensions = 0
    model_id: str | None = None
    for batch in _iter_batches(texts, args.batch_size):
        embeddings = adapter.embed(EmbeddingRequest(texts=batch))
        vectors.extend(embeddings.vectors)
        dimensions = embeddings.dimensions or dimensions
        model_id = model_id or embeddings.model_id

    if dimensions == 0:
        raise RuntimeError("Embedding dimensions not detected")

    os_client.ensure_index(dimensions)
    embeddings_result = EmbeddingResult(
        vectors=vectors,
        model_id=model_id or "unknown",
        dimensions=dimensions,
    )
    logger.debug("ingest: embeddings=%d dims=%d", len(vectors), dimensions)
    documents_to_index = build_index_documents(chunks, embeddings=embeddings_result)
    indexed = bulk_upsert_chunks(os_client.client, os_client.config.index, documents_to_index)
    logger.debug("ingest: indexed=%d index=%s", indexed, os_client.config.index)
    print(f"Ingested {indexed} chunks into index '{os_client.config.index}'.")
    return 0


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(ingest_documents(args))
    except Exception as exc:  # pragma: no cover - CLI safety
        print(f"ingest failed: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
