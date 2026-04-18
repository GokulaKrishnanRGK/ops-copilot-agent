# CLAUDE.md

This file is loaded automatically by Claude Code. It governs all Claude Code behavior in this repository.

---

## Where to Find Information

| What you need | Where to look |
|---|---|
| Current milestone and slice progress | `docs/PROJECT_STATE.md` |
| Milestone definitions, scope, exit criteria | `docs/MILESTONES.md` |
| Development protocol and slice rules | `docs/CODEX_WORKFLOW.md` |
| Hard constraints and out-of-scope items | `docs/CONSTRAINTS.md` |
| System architecture and component boundaries | `docs/ARCHITECTURE_OVERVIEW.md` |
| Tech stack and language rules | `docs/TECH_STACK.md` |
| Agent graph and node definitions | `docs/AGENT.md`, `docs/AGENT_GRAPH.md` |
| LLM gateway design | `docs/LLM_GATEWAY.md` |
| Tool server and MCP contract | `docs/TOOLS.md` |
| RAG pipeline design | `docs/RAG_PIPELINE.md` |
| Database schema and models | `docs/DATA_MODEL.md` |
| SSE event protocol | `docs/EVENT_PROTOCOL.md` |
| Observability and telemetry | `docs/OBSERVABILITY.md` |
| Deployment and environment config | `docs/DEPLOYMENT.md`, `docs/CONFIGURATION.md` |
| Test strategy and targets | `docs/TESTING.md` |
| Project vision | `docs/VISION.md` |

Read `docs/PROJECT_STATE.md` and `docs/MILESTONES.md` before every session. Read the others on demand when working in that area.

---

## Non-Negotiable Rules

- Do not work on more than one milestone at a time.
- Do not work on more than one slice at a time.
- Do not generate flattery, affirmations, or conversational filler.
- Do not use emojis.
- Do not add comments to code.
- Do not refactor unrelated code.
- Do not invent features or requirements not present in project documents.
- Do not stage or commit any Markdown files under `docs/`.
- Do not run `git commit` automatically; human approval is required.
- Do not commit after completing a slice. Produce the Slice Report, then wait for explicit user approval before staging or committing anything. The user will review the code and confirm before the commit and before the next slice begins.
- TypeScript `any` type is prohibited. Use `unknown` and explicit type guards.

Violating any rule is a protocol failure.

---

## Work Protocol

For every slice of work:

1. State the slice goal.
2. List the files that will be changed.
3. Implement the change.
4. Produce a Slice Report in the format defined in `docs/CODEX_WORKFLOW.md`.
5. Ask whether to stage changes with `git add` — only for non-docs files, unless the user explicitly requested staging, committing, or pushing.
6. Stop and wait for approval before continuing.

Do not proceed to the next slice without explicit instruction.

### Slice Report Format

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

- `docs/PROJECT_STATE.md` is the source of truth for what milestone and slice are active.
- All work must stay within the current milestone and slice.
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

## Adapter Pattern Conventions

This project uses a consistent dev/prod adapter pattern for external dependencies:

- Define a protocol (interface) in the appropriate package.
- Provide a no-op or in-memory implementation for unit tests and local dev without external services.
- Provide a real implementation selected by environment variable.
- Callers depend on the protocol only, never on the concrete type.

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
