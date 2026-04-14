# AGENTS.md

This file is the entry point for any automated coding agent operating in this repository.

It exists to ensure required documents are read and enforced before any code is written.

---

## Mandatory Reading

Before making any changes, read and follow these documents in full:

1. docs/CODEX_WORKFLOW.md
2. docs/CONSTRAINTS.md
3. docs/MILESTONES.md

If any of these files are missing or unclear, stop and ask.

---

## Non-Negotiable Rules

- Do not work on more than one milestone at a time.
- Do not work on more than one slice at a time.
- Do not generate flattery, affirmations, or conversational filler.
- Do not use emojis.
- Do not add comments to code.
- Do not refactor unrelated code.
- Do not invent features or requirements.
- Do not stage or commit any Markdown files under docs/.
- Do not ask whether to stage docs/ Markdown changes.

Violating any rule is a protocol failure.

---

## Work Protocol

For every slice of work:

1. State the slice goal.
2. List the files that will be changed.
3. Implement the change.
4. Produce a Slice Report as defined in docs/CODEX_WORKFLOW.md.
5. Ask whether to stage changes with `git add` only for non-docs files unless the user explicitly requested staging, committing, or pushing.
6. If the user explicitly requested it, run `git commit` and `git push` after reviewing the staged changes.
7. After staging, committing, or pushing (if approved or explicitly requested), suggest the next slice and list planned changes.
8. Stop and wait for approval.

Do not proceed without explicit instruction.

---

## Scope Enforcement

- All work must align with the current milestone.
- If a task exceeds slice limits, stop and ask.
- If a requirement is ambiguous, choose the simplest option or ask.
- docs/PROJECT_STATE.md is the source of truth for milestone progress.

---

## Repository Commands

- Install: `make install`
- Build: `make build`
- Lint: `make lint`
- Format check: `make format-check`
- Full checks: `make check`
- Web tests: `make test-web`
- API tests: `make test-api`
- Tool server tests: `make test-tool`
- DB tests: `make test-db`
- LLM gateway tests: `make test-llm`
- RAG tests: `make test-rag`
- Agent runtime tests: `make test-agent`
- Python tools tests: `make test-tools`
- Unit suite: `make test-unit`
- Integration suite: `make test-integration`
- Local smoke: `make smoke-local`
- Local stack: `make run-local`
- Local Helm stack: `make run-local-helm`

---

## Stack Boundaries

- TypeScript is for `apps/web` only.
- Python is for `apps/api` and `packages/*`.
- Go is for `apps/tool-server` only.
- Do not move backend behavior into TypeScript.
- Do not let `apps/api` call the Kubernetes API directly.
- Route all LLM access through `packages/llm-gateway`.
- Keep Kubernetes access read-only and aligned to `K8S_ALLOWED_NAMESPACES`.

---

## Repository Priorities

- Preserve session-oriented persistence and replayability.
- Preserve SSE-first streaming behavior and event ordering.
- Preserve structured telemetry, trace propagation, and cost accounting.
- Keep Terraform outputs, Helm values, and runtime env contracts aligned.
- Prefer reusable contracts and standardization over new abstractions.
- Enforce strict TypeScript typing. Do not introduce `any`.

---

## Codex Local Setup

- Project-local Codex agents live in `.codex/agents/`.
- Use project-local `planner`, `code-reviewer`, `security-reviewer`, and `docs-lookup` when those roles fit the task.
- Use local skill `.agents/skills/mcp-server-patterns/` for MCP server and client contract work.
- Prefer `context7` for current framework and library documentation.

---

## Termination Rule

After producing a Slice Report, stop execution.

Do not continue until explicitly instructed.

This file takes precedence if conflicts arise.
