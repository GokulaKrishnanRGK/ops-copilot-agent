# CLAUDE.md

This file is loaded automatically by Claude Code. It governs all Claude Code behavior in this repository.

---

## Mandatory Reading

Before making any changes, read these documents in full:

1. docs/CODEX_WORKFLOW.md
2. docs/CONSTRAINTS.md
3. docs/MILESTONES.md
4. docs/PROJECT_STATE.md

If any file is missing or unclear, stop and ask.

For deeper context on a specific area, also read:

- docs/VISION.md
- docs/TECH_STACK.md
- docs/ARCHITECTURE_OVERVIEW.md
- docs/AGENT.md / docs/AGENT_GRAPH.md
- docs/LLM_GATEWAY.md
- docs/TOOLS.md
- docs/RAG_PIPELINE.md
- docs/DATA_MODEL.md
- docs/EVENT_PROTOCOL.md
- docs/OBSERVABILITY.md
- docs/DEPLOYMENT.md
- docs/CONFIGURATION.md
- docs/TESTING.md

---

## Non-Negotiable Rules

- Do not work on more than one milestone at a time.
- Do not work on more than one slice at a time.
- Do not generate flattery, affirmations, or conversational filler.
- Do not use emojis.
- Do not add comments to code.
- Do not refactor unrelated code.
- Do not invent features or requirements not present in project documents.
- Do not stage or commit any Markdown files under docs/.
- Do not ask whether to stage docs/ Markdown changes.
- Do not run `git commit` automatically; human approval is required.
- TypeScript `any` type is prohibited. Use `unknown` and explicit type guards.

Violating any rule is a protocol failure.

---

## Work Protocol

For every slice of work:

1. State the slice goal.
2. List the files that will be changed.
3. Implement the change.
4. Produce a Slice Report in the format defined in docs/CODEX_WORKFLOW.md.
5. Ask whether to stage changes with `git add` — only for non-docs files, unless the user explicitly requested staging, committing, or pushing.
6. Stop and wait for approval before continuing.

Do not proceed to the next slice without explicit instruction.

### Slice Report Format

After implementing a slice, output the following and stop:

**Slice Goal** — one or two sentences.

**Files Changed** — list of paths.

**Summary of Changes** — bullet list of what was added or modified.

**How to Run or Test** — exact commands to validate the change.

**Out of Scope** — explicit list of what was not addressed.

**Suggested Commit Message** — one-line conventional commit.

**Suggested Next Slice** — exactly one proposed next step.

### Change Size Limits

Unless explicitly approved:

- Maximum files changed: 10
- Maximum lines added: 400
- Maximum new dependencies: 1

If limits would be exceeded, stop and ask.

---

## Stack Boundaries

- TypeScript is for `apps/web` only.
- Python is for `apps/api` and `packages/*` only.
- Go is for `apps/tool-server` only.
- Do not move backend behavior into TypeScript.
- Do not let `apps/api` call the Kubernetes API directly.
- Route all LLM access through `packages/llm-gateway`.
- Keep Kubernetes access read-only and scoped to `K8S_ALLOWED_NAMESPACES`.

---

## Repository Commands

```
make install          # Install all dependencies
make build            # Build all services
make lint             # Run linters
make format-check     # Check formatting
make check            # Full check suite (lint + format + typecheck)
make test-web         # Web UI tests
make test-api         # API tests
make test-tool        # Tool server tests
make test-db          # DB tests
make test-llm         # LLM gateway tests
make test-rag         # RAG tests
make test-agent       # Agent runtime tests
make test-tools       # Python tools tests
make test-unit        # All unit tests
make test-integration # All integration tests
make smoke-local      # Local smoke run
make run-local        # Start local Docker Compose stack
make run-local-helm   # Start local Helm stack
```

---

## Scope Enforcement

- All work must align with the current milestone in docs/PROJECT_STATE.md.
- docs/PROJECT_STATE.md is the source of truth for milestone progress.
- If a task exceeds slice limits, stop and ask.
- If a requirement is ambiguous, choose the simplest option or ask.

---

## Repository Priorities

- Preserve session-oriented persistence and replayability.
- Preserve SSE-first streaming behavior and event ordering.
- Preserve structured telemetry, trace propagation, and cost accounting.
- Keep Terraform outputs, Helm values, and runtime env contracts aligned.
- Prefer reusable contracts and standardization over new abstractions.
- Enforce strict TypeScript typing. Do not introduce `any`.

---

## Current State (as of last update)

**Active milestone:** L1 — Run budget and gateway visibility in UI

**Remaining slice:**
- Slice 6: Validate a demo run clearly shows provider, model, token usage, estimated cost, and budget state

**Completed milestones:** M0 through M13, L1 slices 1-5

**Upcoming milestones:** L2 through L6 (LinkedIn demo), then M14 onward (eval, per-node routing, caching, summarization, routing).

See docs/MILESTONES.md for full milestone definitions and docs/PROJECT_STATE.md for slice-level progress.

---

## Adapter Pattern Conventions

This project uses a consistent dev/prod adapter pattern for external dependencies:

- Define a protocol (interface) in the appropriate package.
- Provide a no-op or in-memory implementation for unit tests and local dev without external services.
- Provide a real implementation selected by environment variable (e.g., `LANGFUSE_HOST`, `EVAL_DATASET_BUCKET`).
- Callers depend on the protocol only, never on the concrete type.

Examples: `LangfuseAdapter`, `PromptSource`, `DatasetStore`, `SummaryStore`, `RouterPort`.

---

## Contracts Before Implementation

For any new capability:

1. Define interfaces and data contracts first.
2. Define configuration and environment variables.
3. Define persistence or state expectations.
4. Only then implement behavior.

Skipping this order is not allowed.

---

## Termination Rule

After producing a Slice Report, stop execution. Do not continue until explicitly instructed.

This file takes precedence if conflicts arise with other instructions.
