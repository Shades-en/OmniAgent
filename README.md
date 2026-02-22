# OmniAgent

An extensible agent runtime and orchestration framework for building production-grade AI agent systems.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## Features

- **Session Management** - Persistent conversation sessions with MongoDB backend
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
from omniagent.persistence.backends.mongo import MongoBackendAdapter

# In your FastAPI lifespan or startup
async def startup():
    await MongoBackendAdapter.initialize(
        db_name="your_db",
        srv_uri="mongodb+srv://..."
    )

async def shutdown():
    await MongoBackendAdapter.shutdown()
```

### 2. Create a Session Manager

```python
from omniagent.session import MongoSessionManager

session_manager = MongoSessionManager(
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
│   └── mongo.py         # MongoDB connection management
├── exceptions/          # Custom exception hierarchy
├── schemas/
│   └── mongo/           # Beanie ODM models
├── session/
│   ├── base.py          # Abstract SessionManager
│   └── mongo.py         # MongoDB implementation
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
| `OPENAI_API_KEY` | OpenAI API key |

Or pass them directly to `MongoBackendAdapter.initialize()`.

## Schema Imports

Use explicit backend namespaces for schema imports.

```python
from omniagent.schemas.mongo import Session, User, Message, Summary
```

## Consumer Extensions (Favorites)

`starred`/favorite session behavior is intentionally not part of OmniAgent core.
If your app needs favorites, extend `Session` in your consumer app and pass it through `DocumentModels`.

```python
from pydantic import Field

from omniagent.db.document_models import DocumentModels
from omniagent.persistence.backends.mongo import MongoBackendAdapter
from omniagent.schemas.mongo import Message, Session, Summary, User


class CustomSession(Session):
    starred: bool = Field(default=False)

    @classmethod
    async def update_starred_by_client_id(cls, session_id: str, starred: bool, client_id: str) -> dict:
        session = await cls.get_by_id_and_client_id(session_id, client_id)
        if not session:
            return {"session_updated": False, "session_id": session_id, "starred": starred}
        session.starred = starred
        await session.save()
        return {"session_updated": True, "session_id": session_id, "starred": starred}


await MongoBackendAdapter.initialize(
    models=DocumentModels(
        user=User,
        session=CustomSession,
        summary=Summary,
        message=Message,
    )
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

- [ ] Timeouts and retries
- [ ] Guardrails
- [ ] Redis caching
- [ ] Additional LLM providers (Anthropic, Google, etc.)
- [ ] Multi-agent orchestration

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

# TODO

- [ ] Add file upload support in runner flow
