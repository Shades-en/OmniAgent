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
  - Mongo-backed session/state persistence (`session/*`, `schemas/mongo/*`, `db/*`)
  - Streaming + cancellation helpers (`utils/streaming.py`, `utils/task_registry.py`)
  - OpenTelemetry/OpenInference tracing (`utils/tracing.py`)

## Setup Commands
- Check uv exists: `uv --version`
- If `uv` is missing, ask the user to install it first (for example: `brew install uv` on macOS, or see https://docs.astral.sh/uv/getting-started/installation/).
- Sync environment (recommended): `uv sync --dev`
- Runtime-only sync: `uv sync --no-dev`
- Run tests: `uv run pytest`
- Run lint: `uv run pylint src/omniagent`

## Environment And Secrets
- Use `.env.example` as the reference template.
- Key env groups in this repo include provider config (`OPENAI_*`, `LLM_PROVIDER`), Mongo config (`MONGO_*`), tracing flags, and logging settings.

## Repository Map
- `src/omniagent/ai/runner.py`: orchestration flow, tool-call loop, summary generation, streaming entrypoints.
- `src/omniagent/ai/providers/`: provider implementations and streaming event translation.
- `src/omniagent/session/`: session manager abstractions and Mongo implementation.
- `src/omniagent/schemas/mongo/`: Beanie document models and public serialization helpers.
- `src/omniagent/db/`: DB connection and document model wiring.
- `src/omniagent/config.py`: runtime config values from env.
- `src/omniagent/constants.py`: reusable protocol/provider/streaming constants.
- `src/omniagent/exceptions/`: typed exception hierarchy.
- `src/omniagent/utils/tracing.py`: instrumentation and tracing decorators.

## Implementation Rules
- Keep orchestration logic in runtime/session/provider layers, not in ad-hoc helpers.
- Preserve provider abstraction boundaries; route provider-specific behavior through provider modules.
- Use typed exceptions from `omniagent.exceptions`; avoid leaking raw low-level exceptions.
- Keep async paths non-blocking and cancellation-safe, especially around streaming and DB writes.
- Maintain response/schema compatibility for public methods returning message/session payloads.

## Tracing, Streaming, And Session Safety
- Keep tracing instrumentation intact (`instrument`, tracing decorators, context propagation).
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
