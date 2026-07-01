# multi_agent

A FastAPI multi-agent application. A **router agent** (built with LangChain's
`create_agent`) answers each user query by calling specialist **tools** — a
**math agent** and a **history agent**, each implemented as its own **LangGraph**
workflow. A **presenter agent** then rewrites the result in the requested tone.
The router is conversation-aware and routes follow-up questions using chat history.

Everything runs **in a single process / container**: the router calls the math and
history agents in-process (they are exposed to it as tools), and the presenter runs
in-process too.

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
│   └── router_agent.py  #   RouterAgent: create_agent + specialist tools
├── chain/               # Stateless sub-agents (no cross-request memory)
│   ├── base.py          #   BaseChain (invoke contract)
│   ├── math_agent.py    #   MathAgentChain: LangGraph tool-loop workflow
│   ├── history_agent.py #   HistoryAgentChain: LangGraph pure-LLM workflow
│   ├── presenter_agent.py # PresenterAgentChain: tone + fallback handling
│   └── graph.py         #   SimpleGraphChain: minimal LangGraph example
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
    ├── infra/           # Cross-cutting infra (Docker, logging)
    └── settings/        # Configuration (pydantic-settings)
```

A guided, block-by-block walkthrough of the agent code lives in
[`docs/walkthrough/`](docs/walkthrough/00-index.md).

## Agent flow

A request to `POST /api/v1/agent/chat` flows like this:

```
                       POST /api/v1/agent/chat
                  { query, tone, session_id }
                              │
                              ▼
                  ┌───────────────────────┐
                  │   RouterAgent          │
                  │  create_agent(...)     │
                  │  (reads chat history)  │
                  └───────────┬───────────┘
                              │ the agent decides via tool-calling
              ┌───────────────┼───────────────┐
              ▼               ▼                ▼
        solve_math      answer_history     (no tool call)
              │               │                │
              ▼               ▼                ▼
       MathAgentChain   HistoryAgentChain   PresenterAgent.respond()
       (LangGraph:      (LangGraph:          (answer directly OR
        reason→act→      answer node)         ask for more info)
        respond)         -> HistoryResult     -> PresentedResult
        -> MathResult          │                    │
              │                │                     │
              └───────┬────────┘                     │
                      ▼                              │
            PresenterAgent.invoke()                  │
            (restyle in `tone`)                      │
              -> PresentedResult                     │
                      │                              │
                      └─────────────┬───────────────┘
                                    ▼
                          AgentResponse
                  { route, reasoning, answer, details }
                                    │
                                    ▼
                  router records this turn into chat history
```

Step by step:

1. **Read history** — the router loads the conversation for `session_id` from the
   in-memory `ChatHistoryStore`.
2. **Route via tool-calling** — the `create_agent` router runs over the history +
   new query. The agent's own reasoning decides whether to call `solve_math`,
   `answer_history`, or neither (there is no separate classifier step).
3. **Specialists (tools)**
   - `solve_math` → `MathAgentChain`: a LangGraph workflow that loops
     `reason → act (tools) → reason` and finishes with a structured
     `MathResult { answer, steps }`.
   - `answer_history` → `HistoryAgentChain`: a LangGraph workflow whose `answer`
     node returns a structured `HistoryResult { answer, key_facts }`.
   - No tool → the **presenter** answers directly, or asks a clarifying question
     (`needs_more_info = true`) when the request is unclear.
4. **Present** — for the specialist path, the presenter rewrites the structured
   result into a reader-facing message in the requested `tone`
   (`PresentedResult { message, tone, needs_more_info }`).
5. **Remember** — the router appends the user query and final answer back into the
   session history.

The math and history sub-agents are **stateless** (they live under `chain/` and hold
no memory). Only the router keeps conversation history.

### Why these building blocks

- **Router = `create_agent`**: routing is a decision best made by the model itself.
  Exposing the specialists as tools lets the agent pick one, call it, and compose the
  final answer in a single reasoning loop.
- **Specialists = LangGraph**: each specialist is an explicit `StateGraph` with named
  nodes and edges, so the control flow (the math tool-loop, the history answer step)
  is visible and extensible.
- **Presenter = in-process step**: it runs on every turn purely to adjust tone, so it
  is treated as a helper of the router rather than a routable specialist.

## API endpoints

All under `/api/v1`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/chat` | Full flow: route (tool-calling) → present. Body: `{ query, tone, session_id }` |
| POST | `/agent/math` | Call the math agent directly (structured output) |
| POST | `/agent/history` | Call the history agent directly (structured output) |
| POST | `/agent/present` | Call the presenter directly. Body: `{ content, tone }` |
| DELETE | `/agent/sessions/{session_id}` | Clear a conversation's history |
| GET/POST | `/examples`, `/examples/{id}` | Example CRUD resource |
| GET | `/health` | Health check |

## LLM providers

`utility/llm.py` exposes `get_llm(provider, model, temperature)` returning a LangChain
chat model. Choose the backend globally via `LLM_PROVIDER` in `.env`, or per call:

- `openai` → `ChatOpenAI`
- `azure` → `AzureChatOpenAI`
- `ollama` → `ChatOllama` (local)

## Setup

This project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # create .venv and install dependencies
cp .env.example .env    # then set OPENAI_API_KEY (or pick another provider)
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health:   http://127.0.0.1:8000/health
- v1 API:   http://127.0.0.1:8000/api/v1

## Docker

The Dockerfile and Compose file live under `app/core/infra/`. The Dockerfile is a
two-stage build: a **builder** stage that installs dependencies and the project with
`uv`, and a slim **deploy** stage that ships only the built virtual environment and
app code. Compose runs the whole app as a **single container**.

```bash
cp .env.example .env          # optional; set your provider keys
docker compose -f app/core/infra/docker-compose.yml up --build
```

The API is served at http://127.0.0.1:8000. The SQLite database is persisted in the
`app-data` volume.

To also run a local **Ollama** service, enable its profile and point the app at it
(set `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://ollama:11434` in `.env`):

```bash
docker compose -f app/core/infra/docker-compose.yml --profile ollama up --build
```

### Example

```bash
curl -X POST localhost:8000/api/v1/agent/chat \
  -H "content-type: application/json" \
  -d '{"query": "what is the derivative of x^3?", "tone": "friendly", "session_id": "demo"}'
```
