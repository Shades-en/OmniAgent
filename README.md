# OmniAgent

An extensible agent runtime and orchestration framework for building production-grade AI agent systems.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## Features

- **Session Management** - Persistent conversation sessions with MongoDB or PostgreSQL backends
- **Context Orchestration** - Automatic context window management with summarization
- **Multi-Provider Support** - OpenAI Chat Completions and Responses API
- **Tool Calling** - Built-in support for function/tool calling with parallel execution
- **Observability** - OpenTelemetry instrumentation for tracing and monitoring
- **Streaming** - Real-time streaming responses with AI SDK compatible events

## Installation

```bash
pip install omniagent
```

For development:

```bash
git clone https://github.com/Shades-en/OmniAgent.git
cd OmniAgent
pip install -e .
```

## Quick Start

### 1. Initialize the Database

```python
from omniagent.persistence import (
    MongoPersistenceConfig,
    PersistenceBackend,
    get_context,
    initialize_persistence,
    shutdown_persistence,
)

# In your FastAPI lifespan or startup
async def startup():
    await initialize_persistence(
        backend=PersistenceBackend.MONGO,
        backend_config=MongoPersistenceConfig(
            db_name="your_db",
            srv_uri="mongodb+srv://...",
        ),
    )

async def shutdown():
    await shutdown_persistence()
```

Postgres initialization uses `PostgresPersistenceConfig` with either full DSN or split connection keys.

### 2. Create a Session Manager

```python
from omniagent.persistence import get_context

session_manager = get_context().session_manager_cls(
    session_id="session_456",
    user_client_id="client_abc",
)
```

### 3. Run the Agent

```python
from omniagent.ai.runner import Runner
from omniagent.types.chat import MessageQuery

runner = Runner(
    session_manager=session_manager,
    tools=[...],  # Your tools
    system_prompt="You are a helpful assistant.",
)

result = await runner.run(
    query_message=MessageQuery(query="Hello, how are you?"),
)
```

## Architecture

```
omniagent/
├── ai/
│   ├── agents/          # Agent implementations
│   ├── providers/       # LLM providers (OpenAI, etc.)
│   ├── runner.py        # Main orchestration runner
│   └── tools/           # Tool definitions
├── db/
│   ├── mongo/           # MongoDB connection management
│   └── postgres/        # PostgreSQL connection management
├── exceptions/          # Custom exception hierarchy
├── schemas/
│   ├── mongo/           # Beanie ODM models
│   └── postgres/        # SQLAlchemy ORM models
├── session/
│   ├── base.py          # Abstract SessionManager
│   ├── mongo.py         # MongoDB implementation
│   └── postgres.py      # PostgreSQL implementation
├── types/               # Shared types and DTOs
└── utils/               # Utilities (tracing, etc.)
```

## Exception Handling

OmniAgent provides a clean exception hierarchy for error handling:

```python
from omniagent.exceptions import (
    OmniAgentError,        # Base exception
    DatabaseError,         # All DB errors
    NotFoundError,         # Resource not found
    SessionNotFoundError,
    UserNotFoundError,
    AgentError,            # Agent runtime errors
    MaxStepsReachedError,
    ProviderError,         # LLM provider errors
    MessageParseError,
)

# Catch all omniagent errors
try:
    result = await runner.run(query="...")
except NotFoundError as e:
    print(f"Not found: {e.message}")
except OmniAgentError as e:
    print(f"Error: {e.message}, Details: {e.details}")
```

## Configuration

Set these environment variables:

| Variable | Description |
|----------|-------------|
| `MONGO_SRV_URI` | MongoDB connection string |
| `MONGO_DB_NAME` | Database name |
| `POSTGRES_DSN` | Optional full PostgreSQL DSN |
| `POSTGRES_USER` | PostgreSQL username (split config) |
| `POSTGRES_PASSWORD` | PostgreSQL password (split config) |
| `POSTGRES_HOST` | PostgreSQL host (split config) |
| `POSTGRES_PORT` | PostgreSQL port (split config) |
| `POSTGRES_DBNAME` | PostgreSQL database name (split config) |
| `POSTGRES_SSLMODE` | PostgreSQL SSL mode (`require` by default) |
| `OPENAI_API_KEY` | OpenAI API key |
| `LLM_PROVIDER` | Default LLM provider |
| `LLM_API_TYPE` | Default API type (`responses` or `chat_completion`) |
| `LLM_MODEL_PROVIDER_INFERENCE_MAP` | JSON map for model-string -> provider inference |
| `LLM_PROVIDER_DEFAULT_API_TYPE_MAP` | JSON map for provider -> default API type |
| `CHAT_NAME_LLM_PROVIDER` | Provider used by chat-name generation |
| `CHAT_NAME_LLM_API_TYPE` | API type used by chat-name generation |
| `CHAT_NAME_MODEL` | Model used by chat-name generation |
| `CHAT_NAME_TEMPERATURE` | Temperature used by chat-name generation |
| `CHAT_NAME_REQUEST_KWARGS` | Optional JSON kwargs for chat-name generation |

## Agent LLM Config

Agent accepts either a model string (inferred) or an explicit config object.

```python
from omniagent.ai.agents.agent import Agent
from omniagent.types.llm import LLMModelConfig, SummaryLLMOverrides

# Ergonomic model string path (provider/api inferred from env-configured maps)
agent = Agent(
    name="assistant",
    description="General assistant",
    instructions="You are helpful.",
    model="gpt-4.1-mini",
)

# Explicit config path
agent_with_config = Agent(
    name="assistant",
    description="General assistant",
    instructions="You are helpful.",
    model=LLMModelConfig(
        provider="openai",
        api_type="responses",
        model="gpt-4.1-mini",
        temperature=0.7,
        request_kwargs={"max_output_tokens": 1200},
        summary=SummaryLLMOverrides(
            temperature=0.3,
            request_kwargs={"max_output_tokens": 500},
        ),
    ),
)
```

If a model string is not recognized by inference maps, OmniAgent raises a
clear error and asks for an explicit `LLMModelConfig`.

## Schema Imports

Use explicit backend namespaces for schema imports.

```python
from omniagent.schemas.mongo import Session, User, Message, Summary
```

## Consumer Extensions (Favorites)

`starred`/favorite session behavior is intentionally not part of OmniAgent core.
If your app needs favorites, extend backend-specific session/message models in your consumer app and pass them via backend model config during initialization.

```python
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from omniagent.db.postgres import PostgresModels
from omniagent.persistence import (
    PersistenceBackend,
    PostgresPersistenceConfig,
    RepositoryOverrides,
    initialize_persistence,
)
from omniagent.schemas.postgres import Message, Session, Summary, User


class CustomSession(Session):
    starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @classmethod
    async def update_starred_by_client_id(cls, session_id: str, starred: bool, client_id: str) -> dict:
        ...


def wrap_sessions(base_repo):
    return MySessionRepoWithFavorites(base_repo=base_repo, session_model=CustomSession)


await initialize_persistence(
    backend=PersistenceBackend.POSTGRES,
    backend_config=PostgresPersistenceConfig(
        user="postgres",
        password="...",
        host="...",
        port=5432,
        dbname="...",
        models=PostgresModels(
            user=User,
            session=CustomSession,
            summary=Summary,
            message=Message,
        ),
    ),
    repository_overrides=RepositoryOverrides(sessions=wrap_sessions),
)
```

## Observability

OmniAgent is instrumented with OpenTelemetry. To enable tracing:

```python
from omniagent import OmniAgentInstrumentor

# Your tracer provider (you own this)
tracer_provider = TracerProvider(...)

# Instrument OmniAgent runtime spans
OmniAgentInstrumentor().instrument(tracer_provider=tracer_provider)
```

`OmniAgentInstrumentor` configures OmniAgent spans only. OpenAI/PyMongo/LangChain
instrumentation remains consumer-owned and can be enabled separately.

## Roadmap

- [ ] Guardrails
- [ ] Additional LLM providers (Anthropic, Google, etc.)
- [ ] Multi-agent orchestration

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

# TODO
1. Add file upload support in runner flow
2. Remove mock functionality -> Past this make twitter bot (Important)
3. Maybe just maybe the repositories can be made one??