# multi_agent

A FastAPI multi-agent application. A **router agent** classifies each user query
and dispatches it to a specialist sub-agent (math or history), then a
**presenter agent** rewrites the result in the requested tone. The router is
conversation-aware and routes follow-up questions using chat history.

## Project structure

```
app/
├── main.py              # FastAPI app factory & entrypoint
├── routers/             # HTTP routing layer
│   └── v1/              # Versioned API: health, examples, agent
├── services/            # Business logic (example resource)
├── agents/              # Orchestrating agents
│   ├── base.py          #   BaseAgent
│   ├── openai_agent.py  #   single-shot chat agent
│   └── router_agent.py  #   RouterAgent: classify -> dispatch -> present
├── chain/               # Stateless sub-agents (no cross-request memory)
│   ├── math_agent.py    #   MathAgentChain: tool-using ReAct agent
│   ├── history_agent.py #   HistoryAgentChain: pure-LLM tutor
│   └── presenter_agent.py # PresenterAgentChain: tone + fallback handling
├── tools/               # LLM tools (LangChain @tool)
│   ├── calculator.py    #   safe arithmetic (AST)
│   ├── symbolic.py      #   SymPy: solve / derivative / integrate / simplify
│   └── math_helpers.py  #   sqrt, factorial, gcd, lcm, is_prime, mean, median
├── model/               # SQLAlchemy ORM models
├── schema/              # Pydantic request/response schemas
├── database/            # Engine, session, declarative base
├── utility/             # Helpers
│   ├── llm.py           #   get_llm(): OpenAI | Azure | Ollama factory
│   └── history.py       #   ChatHistoryStore (per-session memory)
└── core/
    ├── infra/           # Cross-cutting infra (logging)
    └── settings/        # Configuration (pydantic-settings)
```

## Agent flow

A request to `POST /api/v1/agent/chat` flows through the agents like this:

```
                       POST /api/v1/agent/chat
                  { query, tone, session_id }
                              │
                              ▼
                  ┌───────────────────────┐
                  │      RouterAgent       │
                  │  (reads chat history)  │
                  └───────────┬───────────┘
                              │ classify (structured output: RouteDecision)
              ┌───────────────┼───────────────┐
              ▼               ▼                ▼
          "math"          "history"        "fallback"
              │               │                │
              ▼               ▼                ▼
      MathAgentChain   HistoryAgentChain   PresenterAgent.respond()
      (ReAct + tools)   (pure LLM)         (answer directly OR
       -> MathResult     -> HistoryResult   ask for more info)
              │               │             -> PresentedResult
              └───────┬───────┘                    │
                      ▼                            │
            PresenterAgent.invoke()                │
            (restyle in `tone`)                    │
              -> PresentedResult                   │
                      │                            │
                      └─────────────┬─────────────┘
                                    ▼
                          AgentResponse
                  { route, reasoning, answer, details }
                                    │
                                    ▼
                  router records this turn into chat history
```

Step by step:

1. **Read history** — the router loads the conversation for `session_id` from
   the in-memory `ChatHistoryStore`.
2. **Classify** — the router LLM produces a structured `RouteDecision`
   (`math` | `history` | `fallback`) using the history + the new query, so
   follow-ups ("now solve it") route with context.
3. **Dispatch**
   - `math` → `MathAgentChain`: a LangGraph ReAct agent that calls the math
     tools and returns a structured `MathResult { answer, steps }`.
   - `history` → `HistoryAgentChain`: a pure-LLM tutor returning
     `HistoryResult { answer, key_facts }`.
   - `fallback` → the **presenter** answers the query directly, or asks a
     clarifying question (`needs_more_info = true`) when the request is unclear.
4. **Present** — for math/history, the presenter rewrites the structured result
   into a reader-facing message in the requested `tone`
   (`PresentedResult { message, tone, needs_more_info }`).
5. **Remember** — the router appends the user query and final answer back into
   the session history.

The math and history sub-agents are **stateless** (they live under `chain/` and
hold no memory). Only the router keeps conversation history.

## API endpoints

All under `/api/v1`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/chat` | Full flow: route → solve → present. Body: `{ query, tone, session_id }` |
| POST | `/agent/math` | Call the math agent directly (structured output) |
| POST | `/agent/history` | Call the history agent directly (structured output) |
| POST | `/agent/present` | Call the presenter directly. Body: `{ content, tone }` |
| DELETE | `/agent/sessions/{session_id}` | Clear a conversation's history |
| GET/POST | `/examples`, `/examples/{id}` | Example CRUD resource |
| GET | `/health` | Health check |

## LLM providers

`utility/llm.py` exposes `get_llm(provider, model, temperature)` returning a
LangChain chat model. Choose the backend globally via `LLM_PROVIDER` in `.env`,
or per call:

- `openai` → `ChatOpenAI`
- `azure` → `AzureChatOpenAI`
- `ollama` → `ChatOllama` (local)

## Setup

This project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # create .venv and install dependencies
cp .env.example .env    # then set OPENAI_API_KEY (or pick another provider)
```

(Or with pip: `pip install -r requirements.txt`.)

## Run

```bash
uv run uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health:   http://127.0.0.1:8000/health
- v1 API:   http://127.0.0.1:8000/api/v1

## Docker

The Dockerfile and Compose file live under `app/core/infra/`. The Dockerfile is
a two-stage build: a **builder** stage that installs dependencies and the
project with `uv`, and a slim **deploy** stage that ships only the built virtual
environment and app code.

```bash
cp .env.example .env          # optional; set your provider keys
docker compose -f app/core/infra/docker-compose.yml up --build
```

The API is served at http://127.0.0.1:8000. The SQLite database is persisted in
the `app-data` volume.

To also run a local **Ollama** service, enable its profile and point the app at
it (set `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://ollama:11434` in `.env`):

```bash
docker compose -f app/core/infra/docker-compose.yml --profile ollama up --build
```

### Example

```bash
curl -X POST localhost:8000/api/v1/agent/chat \
  -H "content-type: application/json" \
  -d '{"query": "what is the derivative of x^3?", "tone": "friendly", "session_id": "demo"}'
```
