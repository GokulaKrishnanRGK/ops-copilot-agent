# OpsCopilot

OpsCopilot is a governed, read-only Kubernetes operations copilot built on a graph-based agent runtime. Every design decision favors explicitness, observability, and bounded execution over autonomy.

---

## What It Does

OpsCopilot answers Kubernetes diagnostic questions in natural language. It plans a multi-step investigation, executes read-only tool calls against your cluster, retrieves relevant operational knowledge from a document index, and synthesizes a grounded answer — all within configurable step, cost, and time limits.

---

## Core Capabilities

- Graph-based agent execution with explicit control flow (no hidden loops)
- Prompt injection guard as the outermost layer — regex + optional LLM classifier
- Read-only Kubernetes diagnostics: pods, events, logs, deployments
- Per-node model routing — scope/clarifier/answer on Haiku, planner on Sonnet
- Prompt caching on all system messages (Bedrock Converse `cachePoint`)
- RAG pipeline over static operational documents with citations
- Conversation summarization — sliding window keeps token growth bounded
- Budget, cost, and token usage visible per run in the UI
- Runtime settings page — model IDs, limits, eval flags, embedding model, all configurable without redeployment
- Online eval sampling with LLM-as-judge and RAGAS scores via Langfuse
- End-to-end observability: OpenTelemetry traces, Prometheus metrics, Loki logs, Grafana

---

## Architecture

| Component | Role |
|---|---|
| `apps/web` | React chat UI — streaming transcript, tool timeline, budget display, settings page |
| `apps/api` | FastAPI backend — sessions, SSE streaming, settings API, agent invocation |
| `packages/agent-runtime` | LangGraph agent graph — injection_guard → scope_check → planner → tool_executor → answer |
| `packages/llm-gateway` | LiteLLM wrapper — budget enforcement, cost ledger, idempotency, OTel instrumentation |
| `packages/rag` | Document ingestion, Bedrock embeddings, OpenSearch kNN retrieval, citations |
| `packages/db` | SQLAlchemy models, Alembic migrations, repositories |
| `packages/observability` | OpenTelemetry + OpenLLMetry (Bedrock) + Langfuse adapter |
| `apps/tool-server` | Go MCP server — read-only Kubernetes API calls with namespace allowlist, redaction, timeouts |

All LLM calls are routed through `packages/llm-gateway`. No agent node calls Bedrock directly.

---

## Agent Execution Flow

```
User prompt
  → injection_guard     (regex + optional LLM scan; blocks injections immediately)
  → scope_check         (Haiku — is this a Kubernetes / knowledge query?)
  → summarizer          (Haiku — compact history older than N turns into a summary paragraph;
                          no-op below the window threshold)
  → planner             (Sonnet — multi-step plan from prompt + RAG context + summary)
  → clarifier           (Haiku — resolve missing args; skipped if all args present)
  → tool_executor       (MCP calls to tool-server per plan step)
  → answer              (Haiku — synthesize grounded response from tool results + RAG)
  → SSE stream to UI
```

Each step is streamed to the client, persisted to PostgreSQL, and traced in OTel.

---

## Local Quick Start

**Prerequisites:** Docker, Docker Compose, Kind, kubectl, AWS credentials with Bedrock access.

```bash
cp .env.example .env          # fill in AWS credentials and other required vars
make run-local                # creates Kind cluster, seeds workloads, starts all services
```

Services:

| Service | URL |
|---|---|
| Web UI | http://localhost:5173 |
| API | http://localhost:8000 |
| Grafana | http://localhost:3000 (admin / admin) |
| Langfuse | http://localhost:3001 |

The `db-migrate` container runs `alembic upgrade head` before the API starts.

---

## Cloud Deployment (EKS)

Infrastructure is provisioned with Terraform and deployed with Helm.

```bash
terraform -chdir=deploy/terraform apply          # VPC, RDS, OpenSearch, EKS, ECR, IRSA roles
make eks-kubeconfig                              # pull kubeconfig for EKS cluster
make ecr-build-push                              # build and push images to ECR
make helm-app-values-generate                   # render Helm values from Terraform outputs
make eks-secrets-sync                            # sync secrets → Kubernetes Secret
make helm-app-up                                 # install/upgrade chart (runs Alembic Job first)
```

The Helm chart provisions a pre-install migration Job, RBAC for the tool-server ServiceAccount, and Ingress with ACM TLS via AWS Load Balancer Controller.

---

## Observability

- **Traces** — Tempo (via OTel Collector), one trace per agent run covering all node spans, LLM calls, tool calls, and RAG retrieval
- **Metrics** — Prometheus + Grafana; counters and histograms for runs, LLM cost, tool latency, RAG chunks
- **Logs** — Loki via Grafana Alloy log shipper
- **Langfuse** — prompt registry, trace viewer, LLM-as-judge and RAGAS scores, experiment tracking

Set `OTEL_EXPORTER_OTLP_ENDPOINT` to the OTLP base URL (e.g. `http://localhost:4318`). Both local and EKS deployments use the same telemetry schema.

---

## Safety and Constraints

- All Kubernetes access is read-only (no write verbs in RBAC or tool-server)
- Namespace allowlist enforced at both RBAC and software layers
- Prompt injection guard runs before any LLM call
- Execution bounded by step count (`max_agent_steps`), LLM call count, wall-clock time, and USD budget
- No unbounded agent loops; all termination conditions are deterministic

---

## License

TBD
