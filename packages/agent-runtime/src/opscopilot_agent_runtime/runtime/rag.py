from __future__ import annotations

import os
from dataclasses import dataclass

from opscopilot_rag.citations import build_citations
from opscopilot_rag.embeddings import OpenAIEmbeddingAdapter
from opscopilot_rag.opensearch_client import OpenSearchClient
from opscopilot_rag.retrieval import retrieve_knn
from opscopilot_rag.types import EmbeddingRequest, OpenSearchConfig, \
  RetrievalResult, Citation

from opscopilot_agent_runtime.runtime.logging import get_logger


@dataclass(frozen=True)
class RagContext:
  text: str
  results: list[RetrievalResult]
  citations: list[Citation]


def _read_top_k() -> int:
  raw = os.getenv("RAG_TOP_K", "3")
  try:
    return max(1, int(raw or "3"))
  except ValueError as exc:
    raise RuntimeError("RAG_TOP_K must be an integer") from exc


class RagRetriever:
  def __init__(self, config: OpenSearchConfig, top_k: int) -> None:
    self._config = config
    self._top_k = top_k
    self._client = OpenSearchClient(config).client
    self._adapter = OpenAIEmbeddingAdapter()

  @staticmethod
  def from_env() -> "RagRetriever":
    return RagRetriever(OpenSearchClient().config, _read_top_k())

  def retrieve(self, query: str) -> RagContext:
    logger = get_logger(__name__)
    logger.info(
        "RAG RETRIEVE query %s index=%s top_k=%d", query, self._config.index,
        self._top_k
    )
    embeddings = self._adapter.embed(EmbeddingRequest(texts=[query]))
    vector = embeddings.vectors[0]
    results = retrieve_knn(self._client, self._config.index, vector,
                           self._top_k)
    citations = build_citations(results)
    context_lines = []
    for result in results:
      context_lines.append(f"[{result.source}] {result.text}")
    if os.getenv("AGENT_DEBUG") == "1":
      logger.info(
          "rag retrieved %d chunks index=%s top_k=%d",
          len(results),
          self._config.index,
          self._top_k,
      )
    return RagContext(text="\n".join(context_lines), results=results, citations=citations)
