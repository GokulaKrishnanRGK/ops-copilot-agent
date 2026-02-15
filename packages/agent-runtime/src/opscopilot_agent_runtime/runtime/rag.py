from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from opentelemetry import metrics, trace
from opscopilot_rag.citations import build_citations
from opscopilot_rag.embeddings import OpenAIEmbeddingAdapter
from opscopilot_rag.opensearch_client import OpenSearchClient
from opscopilot_rag.retrieval import retrieve_knn
from opscopilot_rag.types import EmbeddingRequest, OpenSearchConfig, \
  RetrievalResult, Citation

from opscopilot_agent_runtime.runtime.logging import get_logger

if TYPE_CHECKING:
  from opscopilot_agent_runtime.persistence import AgentRunRecorder


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
    meter = metrics.get_meter("opscopilot_agent_runtime.rag")
    self._rag_retrieval_requests_total = meter.create_counter("rag_retrieval_requests_total")
    self._rag_retrieval_latency_ms = meter.create_histogram("rag_retrieval_latency_ms")
    self._rag_retrieved_chunks_total = meter.create_counter("rag_retrieved_chunks_total")

  @staticmethod
  def from_env() -> "RagRetriever":
    return RagRetriever(OpenSearchClient().config, _read_top_k())

  def retrieve(self, query: str, recorder: "AgentRunRecorder | None" = None) -> RagContext:
    logger = get_logger(__name__)
    tracer = trace.get_tracer("opscopilot_agent_runtime.rag")
    started = time.perf_counter()
    with tracer.start_as_current_span("rag.retrieve") as span:
      span.set_attribute("index", self._config.index)
      span.set_attribute("top_k", self._top_k)
      span.set_attribute("query_length", len(query))
      self._rag_retrieval_requests_total.add(1, {"index": self._config.index})
      if recorder:
        span.set_attribute("session_id", recorder.session_id)
        span.set_attribute("agent_run_id", recorder.run_id)
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
      span.set_attribute("retrieved_chunks", len(results))
      self._rag_retrieved_chunks_total.add(len(results), {"index": self._config.index})
      self._rag_retrieval_latency_ms.record(
          (time.perf_counter() - started) * 1000.0,
          {"index": self._config.index},
      )
      logger.debug(
          "rag retrieved %d chunks index=%s top_k=%d",
          len(results),
          self._config.index,
          self._top_k,
      )
      return RagContext(text="\n".join(context_lines), results=results, citations=citations)
