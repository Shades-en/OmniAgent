# AGENTS.md

## Scope And Precedence
- This file applies to the entire OmniAgent repository.
- Direct user instructions in chat override this file.
- If nested `AGENTS.md` files are added later, the nearest file to the changed code takes precedence for that scope.

## Project Overview
- OmniAgent is an extensible agent runtime and orchestration framework.
- Main package path: `src/omniagent`.
- Core capabilities:
  - Agent orchestration via `ai/runner.py`
  - Provider abstraction (`ai/providers/*`)
  - Startup-selected backend persistence (`session/*`, `schemas/*`, `db/*`, `persistence/backends/*`)
  - Streaming + cancellation helpers (`utils/streaming.py`, `utils/task_registry.py`)
  - OpenTelemetry/OpenInference tracing (`tracing/*`)

## Setup Commands
- Check uv exists: `uv --version`
- If `uv` is missing, ask the user to install it first (for example: `brew install uv` on macOS, or see https://docs.astral.sh/uv/getting-started/installation/).
- Sync environment (recommended): `uv sync --dev`
- Runtime-only sync: `uv sync --no-dev`
- Run tests: `uv run pytest`
- Run lint: `uv run pylint src/omniagent`

## Environment And Secrets
- Use `.env.example` as the reference template.
- Key env groups in this repo include provider config (`OPENAI_*`, `LLM_PROVIDER`), persistence backend config (`MONGO_*`, `POSTGRES_*`), tracing flags, and logging settings.

## Repository Map
- `src/omniagent/ai/runner.py`: orchestration flow, tool-call loop, summary generation, streaming entrypoints.
- `src/omniagent/ai/providers/`: provider implementations and streaming event translation.
- `src/omniagent/session/`: session manager abstractions and backend implementations (`mongo.py`, `postgres.py`).
- `src/omniagent/schemas/mongo/`: Mongo (Beanie) schema models.
- `src/omniagent/schemas/postgres/`: Postgres (SQLAlchemy) schema models.
- `src/omniagent/db/mongo/`: Mongo DB init/model registry.
- `src/omniagent/db/postgres/`: Postgres engine/bootstrap/model registry.
- `src/omniagent/persistence/backends/mongo/`: Mongo adapter, contracts, repositories.
- `src/omniagent/persistence/backends/postgres/`: Postgres adapter, contracts, repositories.
- `src/omniagent/config.py`: runtime config values from env.
- `src/omniagent/constants/`: reusable protocol/provider/streaming constants.
- `src/omniagent/exceptions/`: typed exception hierarchy.
- `src/omniagent/tracing/`: tracing runtime state, context, decorators, graph helpers, and instrumentation support.

## Backend Organization Rules
- Keep all backend-specific code under explicit backend folders (`mongo/`, `postgres/`).
- Do not place backend-specific implementations in shared root files when backend folders exist.
- For backend schema packages, keep one model per file (`user.py`, `session.py`, `message.py`, `summary.py`).
- `models.py` in schema packages may only aggregate exports; it must not contain full model implementations.
- When adding support for another backend/system, move any cross-backend shared logic into higher-level abstractions (`base.py`, shared utilities, or contracts) instead of duplicating behavior in each backend module.

## Implementation Rules
- Keep orchestration logic in runtime/session/provider layers, not in ad-hoc helpers.
- Preserve provider abstraction boundaries; route provider-specific behavior through provider modules.
- Use typed exceptions from `omniagent.exceptions`; avoid leaking raw low-level exceptions.
- Keep async paths non-blocking and cancellation-safe, especially around streaming and DB writes.
- Maintain response/schema compatibility for public methods returning message/session payloads.
- Whenever changing schemas, document models, or repository methods/contracts, update corresponding protocol definitions and the backend-specific model contracts in `src/omniagent/persistence/backends/<backend>/model_contracts.py` in the same change.
- Hard rule: do not keep duplicate module surfaces or compatibility shims after architectural moves. When a module is moved/renamed, update all imports and remove the old module in the same change unless the user explicitly requests backward compatibility.
- Prioritize parallelization for independent IO-bound work (independent reads, unrelated external calls, filesystem scans) when behavior is deterministic.
- Never parallelize queries/mutations that share the same DB session/transaction/connection (for example SQLAlchemy `AsyncSession`); keep those steps sequential unless you intentionally split into separate isolated sessions.

## Post-Implementation Cleanup
- After implementing any plan, run a repository-wide cleanup pass before finalizing.
- Remove redundant files, stale imports, unused variables/constants, dead helper functions, and obsolete compatibility code.
- Verify moved modules have no old-path references left in code, tests, or docs.

## New DB Backend Checklist
- Add backend enum/config support in persistence types and initialization dispatch.
- Add `db/<backend>/` lifecycle modules (engine/client init, bootstrap, model registry).
- Add `schemas/<backend>/` with per-model files and package exports.
- Add `persistence/backends/<backend>/model_contracts.py` and repository implementations.
- Add backend session manager implementation in `session/<backend>.py`.
- Wire backend adapter into `initialize_persistence` and export surfaces.
- Update docs/examples/env templates for backend configuration and startup usage.
- Run compile/tests and then complete the cleanup pass for stale backend references.

## Tracing, Streaming, And Session Safety
- Keep tracing instrumentation intact (`OmniAgentInstrumentor`, tracing decorators, context propagation).
- Preserve streaming protocol/event compatibility; do not change event names/payload shape without explicit approval.
- Ensure streaming cancellation behavior remains correct (task register/unregister and cleanup).
- Keep session ownership/state transitions consistent when updating messages, summaries, and sessions.
- For context/summarization thresholds, prefer config-driven updates.

## Validation Before Finishing
- Preferred checks:
  - `uv run pytest`
  - `uv run pylint src/omniagent`
- Minimum sanity check if full tests are unavailable:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache uv run python -m compileall src/omniagent`

## Important Do-Nots
- Do not commit secrets or sensitive env values.
- Do not bypass exception typing/handling boundaries with generic catch-all logic unless justified.
- Do not break SSE/streaming protocol compatibility unintentionally.
- Do not remove tracing or cancellation cleanup paths in runner/session flows.

## Current Architecture Decisions
- Do not prioritize backward compatibility unless the user explicitly asks for it.
