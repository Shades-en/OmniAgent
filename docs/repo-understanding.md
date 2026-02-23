# OmniAgent Repository Understanding

This document captures a high-level, code-grounded understanding of OmniAgent's architecture, execution flow, and extension points.

## Purpose

OmniAgent provides a runtime for:
- Session-aware AI chat orchestration.
- Provider-abstracted LLM calls (currently OpenAI Responses + Chat Completions).
- Tool calling with iterative loops and step limits.
- MongoDB-backed persistence for users, sessions, messages, and summaries.
- SSE-compatible streaming and cancellation support.
- OpenTelemetry/OpenInference tracing.

## Runtime Flow (Query Lifecycle)

1. Consumer creates an `Agent` (instructions + tools), a `SessionManager`, and a `Runner`.
2. `Runner.run` / `Runner.run_stream` enters `_run_with_optional_stream`.
3. The runner asks the session manager for context and state updates.
4. `_handle_query` performs a tool-call loop until the turn is complete:
   - Build user and AI message DTOs.
   - Generate response + summary concurrently.
   - If tool calls are requested, execute tools and iterate.
   - Enforce `MAX_STEPS`.
5. Persist messages and optional regenerated summary through `SessionManager.update_user_session`.
6. In streaming mode:
   - Emit protocol events during generation.
   - Emit `finish` only after DB writes complete.
   - Emit `data-session` event with persisted result.

## Main Architectural Layers

### 1) Orchestration (`src/omniagent/ai`)
- `runner.py`: central orchestrator for normal + streaming execution, tool-call loop, fallback behavior, and persistence handoff.
- `agents/agent.py`: lightweight agent container (`name`, `instructions`, `tools`, optional callbacks).
- `tools/tools.py`: abstract tool contract with required `Arguments` pydantic schema and traced invocation.

### 2) Provider Abstraction (`src/omniagent/ai/providers`)
- `llm_provider.py` defines the provider interface for response generation, summaries, chat naming, and system-message construction.
- `providers/__init__.py` resolves provider implementation via `get_llm_provider` and provider options (e.g., OpenAI API type).
- OpenAI-specific modules implement translation between OpenAI events and OmniAgent's streaming protocol.

### 3) Session and Context Management (`src/omniagent/session`)
- `SessionManager` (abstract): shared state machine for turn counters, token/summary thresholds, and context-window composition.
- `MongoSessionManager`: Mongo-specific user/session fetching, context retrieval, summary persistence, and message insertion.

### 4) Persistence and Contracts (`src/omniagent/persistence`, `src/omniagent/db`, `src/omniagent/schemas`)
- `MongoBackendAdapter.initialize()` validates model protocol/repository contracts before DB initialization.
- `MongoDB.init()` wires Beanie with configured document model classes and forward-reference rebuilds.
- `DocumentModels` enables consumer-level schema extension while enforcing required interface compatibility.
- `schemas/mongo/*` holds canonical Beanie documents for `User`, `Session`, `Message`, `Summary`.

### 5) Tracing (`src/omniagent/tracing`)
- `trace_method`/`trace_operation` wrap runtime, DB, and tool execution with spans.
- `OmniAgentInstrumentor` injects tracer provider wiring for library-owned spans.
- State transitions can be attached to current spans through `track_state_change`.

### 6) Utilities (`src/omniagent/utils`)
- `streaming.py`: SSE header + event formatting helpers.
- `task_registry.py`: in-memory active task registry for stream cancellation by `session_id`.
- `general.py`: shared helpers (ID generation, env parsing, etc.).

## Extension Points

- **Custom Models**: pass a `DocumentModels` instance into `MongoBackendAdapter.initialize()` to use custom document classes.
- **New Providers**: implement `LLMProvider` abstract methods and update provider resolution.
- **New Tools**: subclass `Tool`, define `Arguments`, implement async `__call__`.
- **Frontend Protocol Integrations**: consume SSE events emitted by `Runner.run_stream` (`data: {json}` with `[DONE]` sentinel).

## Safety and Operational Characteristics

- Tool-call loops are bounded by `MAX_STEPS`.
- Streaming persistence path shields DB writes from cancellation to avoid partial-loss on user interrupt.
- Failures in query handling can produce fallback messages and optional streamed fallback output.
- Tracing is optional/configurable and preserves context metadata (session/user/turn).

## Public Surface (Key Exports)

`omniagent.__init__` exposes:
- `OmniAgentInstrumentor`
- `setup_logging`
- `SessionManager`
- `MongoSessionManager`

The expected startup lifecycle is:
1) `MongoBackendAdapter.initialize(...)`
2) Run agent operations
3) `MongoBackendAdapter.shutdown()`
