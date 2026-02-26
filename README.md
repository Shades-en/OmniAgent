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
from omniagent.persistence import (
    PersistenceBackend,
    get_context,
    initialize_persistence,
    shutdown_persistence,
)

# In your FastAPI lifespan or startup
async def startup():
    await initialize_persistence(
        backend=PersistenceBackend.MONGO,
        db_name="your_db",
        srv_uri="mongodb+srv://...",
    )

async def shutdown():
    await shutdown_persistence()
```

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
If your app needs favorites, extend `Session` in your consumer app and pass it through `DocumentModels`.

```python
from pydantic import Field

from omniagent.db.document_models import DocumentModels
from omniagent.persistence import PersistenceBackend, initialize_persistence
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


await initialize_persistence(
    backend=PersistenceBackend.MONGO,
    models=DocumentModels(
        user=User,
        session=CustomSession,
        summary=Summary,
        message=Message,
    ),
)
```

Consumer apps can register optional extension repositories on the active persistence context.

```python
from omniagent.persistence import (
    get_context,
    register_extension,
)

register_extension(name="favorites", repo=my_favorites_repo, capability="favorites")

ctx = get_context()
favorites_repo = ctx.extensions["favorites"]
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
- [ ] remove mock functionality
- [ ] initialize_persistence method is using alot of mongospecific variables.