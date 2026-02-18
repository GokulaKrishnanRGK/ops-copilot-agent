# OpsCopilot

OpsCopilot is a Kubernetes operations copilot built around a bounded, graph-based LLM execution model. It performs diagnostic analysis on Kubernetes workloads using read-only tooling, explicit control flow, and production-grade governance around cost, timeouts, and observability.

The system is designed to run locally and in Kubernetes without architectural changes.

---

## Overview

Modern operational tooling increasingly relies on LLMs, but most examples hide control flow, lack observability, and ignore operational constraints.

OpsCopilot takes a different approach:

- Agent execution is explicitly modeled as a graph
- All tool usage is read-only and bounded
- LLM usage is centralized, budgeted, and observable
- Every execution step is inspectable and replayable

The result is a transparent, debuggable system for Kubernetes diagnostics.

---

## Core Capabilities

- Interactive chat interface with streaming responses
- Graph-based agent execution (planner, tool executor, optional critic, finalizer)
- Read-only Kubernetes diagnostics (pods, events, logs, deployments)
- Retrieval-augmented context from static operational documents
- Per-step cost and usage accounting
- Deterministic stopping conditions
- End-to-end observability with OpenTelemetry

---

## High-Level Architecture

### Components

- **Web UI**
  - React-based chat interface
  - Streaming output and execution timeline

- **API Backend**
  - Session management
  - Streaming transport
  - Persistence and orchestration entrypoint

- **Agent Runtime**
  - Explicit graph-based control flow
  - Bounded execution with limits and budgets

- **LLM Gateway**
  - Centralized abstraction for all LLM calls
  - Cost accounting, budget enforcement, retries, timeouts

- **Tool Layer**
  - Read-only Kubernetes diagnostic tools
  - Strict timeouts and output limits

- **RAG Pipeline**
  - Minimal retrieval over static documents
  - Context injection with citations

- **Persistence**
  - Relational database for runs, tool calls, LLM calls, and budgets

- **Observability**
  - OpenTelemetry traces, metrics, and structured logs

---

## Execution Flow

1. A user submits a diagnostic query via the UI.
2. The backend starts a new agent run and opens a streaming channel.
3. The agent planner produces a structured diagnostic plan.
4. Kubernetes tools are executed step by step.
5. Retrieved context may be injected where relevant.
6. An optional critique step may trigger replanning.
7. A final response is synthesized with evidence and usage data.
8. Execution terminates deterministically when limits are reached.

All steps are streamed to the client and persisted.

---

## Example Scenario

User query:
`Why is my pod crash-looping?`

The system may:

- Describe the pod
- Fetch recent events
- Retrieve recent container logs
- Identify a failure cause
- Cite tool output and retrieved documentation
- Report execution cost and usage

---

## Local Development

### Prerequisites

- Docker
- Docker Compose
- Kind
- kubectl

### Local Startup

1. Create a local Kubernetes cluster:
   `./scripts/create-kind.sh`
2. Start the system:
   `docker compose up`

3. Open the web UI and run a diagnostic query.

---

## Kubernetes Deployment (EKS)

OpsCopilot is deployable to Kubernetes using Helm.

- Same containers as local development
- Configuration via Helm values
- External database supported

Example:
`helm install opscopilot ./deploy/helm/opscopilot -f ./deploy/helm/opscopilot/values.yaml`

---

## Observability

The system emits:

- Distributed traces for agent runs, tool calls, and LLM calls
- Metrics for latency, errors, and cost
- Structured logs correlated by trace and run identifiers

Local deployments include a full observability stack for inspection in Grafana.

Run collector locally:

- `make observability-up`
- Grafana: `http://localhost:3000` (default: `admin` / `admin`)
- Loki API: `http://localhost:3100`
- Tempo API: `http://localhost:3200`
- Prometheus UI: `http://localhost:9090`
- Collector health: `http://localhost:13133/`
- OTLP HTTP endpoint: `http://localhost:4318`
- Collector Prometheus scrape endpoint: `http://localhost:8889/metrics`

The Grafana data sources are provisioned automatically:

- `Prometheus` for metrics
- `Loki` for logs
- `Tempo` for traces
- Dashboards are provisioned automatically in folder `OpsCopilot`:
  - `OpsCopilot Overview`
  - `OpsCopilot Logs and Traces`

Logs are ingested via Grafana Alloy from `${LOGS_HOST_PATH}` (for example API and tool-server JSON log files).

Runtime export configuration:

- Set `OTEL_EXPORTER_OTLP_ENDPOINT` to the OTLP base URL, for example `http://localhost:4318`.
- Endpoint validation is strict: URL must be `http(s)` and must not include a path like `/v1/traces`.
- The tool-server also uses `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME` for trace export.
- Invalid endpoint values fail fast at startup.

---

## Constraints and Safety

- All Kubernetes access is read-only
- Execution is bounded by step count, time, and budget
- No background or unbounded agent loops
- Failures are explicit and observable

---

## Non-Goals

- No mutating cluster actions
- No autonomous long-running agents
- No model fine-tuning
- No multi-tenant optimization
- No production security hardening

---

## License

TBD
