# Locus

**A local-first personal knowledge assistant that builds a live knowledge graph from natural conversation.**

You talk to Locus like you'd talk to a friend. Behind the scenes, it extracts the people, projects, and relationships you mention, writes them into a graph database, and grounds every future answer in that graph, so it actually *knows things about you* instead of hallucinating. Everything runs on your own machine. No API keys, no data leaving your laptop.

Built by Rishi Thakkar.

---

## Why this project is worth 3 minutes of your time

Most "AI chat" projects are a thin wrapper around an API call. Locus is a small distributed system that solves the harder problem underneath a real memory product: **how do you turn unstructured conversation into durable, queryable structured knowledge, and then use that knowledge to keep the model honest?**

That required making real engineering decisions about:

- **Grounding vs. hallucination** — the model is only allowed to answer from verified facts in the graph
- **Latency vs. completeness** — knowledge extraction happens *after* the response is sent, so chat stays fast
- **Cost vs. capability** — a dual-model setup uses a small model for cheap structured extraction and a larger one only where reasoning matters
- **Privacy vs. convenience** — the entire stack is local, which is a deliberate product stance, not an accident

The rest of this README walks through those decisions.

---

## Architecture

```
┌──────────────┐        ┌───────────────────────────────────────┐
│  CLI client  │        │              FastAPI backend            │
│  (Rich TUI)  │──POST──▶│                                         │
└──────────────┘ /chat  │  1. retrieve context from graph         │
                        │  2. generate grounded reply (chat model)│
┌──────────────┐        │  3. return reply immediately            │
│ React + Vite │──GET──▶│  4. extract entities  ── background ──┐ │
│  graph view  │ /graph │                                       │ │
└──────────────┘        └───────────────────────────────────────┼─┘
                                                                 │
      ┌──────────────┐     ┌──────────────┐     ┌───────────────▼─┐
      │    SQLite    │     │    Ollama    │     │      Neo4j       │
      │ chat history │     │  local LLMs  │     │  knowledge graph │
      └──────────────┘     └──────────────┘     └──────────────────┘
```

**The request lifecycle that matters:**

1. A message hits `POST /chat`.
2. Locus pulls relevant facts out of Neo4j (a lightweight GraphRAG retrieval step).
3. Those facts are injected into the system prompt, and the chat model answers **grounded strictly in that context**.
4. The reply is returned to the user *immediately*.
5. A **background task** then runs a second, cheaper model to extract new entities/relationships and upsert them into the graph.

The user never waits on extraction. The graph gets smarter with every message. That's the whole product loop.

---

## The engineering decisions I'd want a founder to notice

### 1. Two models, chosen for the job — not one model for everything
`app/services/ollama.py` wires up three configurable models: a strong chat model (`qwen2.5-coder:14b`), a small extractor model (`qwen2.5:7b`), and an embedding model. Structured JSON extraction doesn't need a 14B reasoning model, so it doesn't get one. This is the kind of cost/latency tradeoff that matters at scale, prototyped early.

### 2. Extraction is async, so the product feels fast
Entity extraction is the slowest step. Instead of blocking the response on it, `main.py` hands it to a FastAPI `BackgroundTasks` job (`maybe_update_graph`). Perceived latency is just the chat generation; the graph catches up a beat later.

### 3. A cheap classifier gates the expensive extraction
Not every message contains new knowledge. Before running the extractor, `needs_extraction()` does a fast keyword check for explicit commands (`add`, `delete`, `forget`...) and otherwise asks a tiny yes/no classifier "does this mention 2+ named entities?" If not, extraction is skipped entirely. Small optimization, big compounding savings.

### 4. Grounded generation with an explicit cold-start mode
The chat endpoint runs in one of two prompt modes:
- **Grounded mode** — facts exist in the graph, so the model is instructed to answer *only* from them and ignore outside knowledge.
- **Cold-start mode** — no facts yet, so the model is explicitly told not to invent details and to ask the user for more instead.

This is the anti-hallucination design. The model isn't trusted to "know" who Rishi is; it's only trusted to phrase facts the graph already verified.

### 5. Natural-language deletions, not just inserts
Memory that can only grow is a bug. The extractor prompt (`extractor.py`) handles negation: *"ashley has nothing to do with locus"* produces a `deletions` payload, and `neo4jService.upsertGraph()` removes just that edge, without nuking the underlying nodes. Edge-level vs. node-level deletion is handled deliberately.

### 6. Entity resolution baked into extraction
"rishi", "rishi thakkar", and "Rishi" all resolve to a single canonical node id via explicit resolution rules in the extractor prompt. This is the unglamorous work that keeps a knowledge graph from fragmenting into duplicate nodes.

### 7. Defensive parsing of LLM output
LLMs don't reliably return clean JSON. The extractor regex-extracts the JSON object from whatever the model wraps around it and fails soft to an empty result rather than crashing the request.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | **FastAPI** + Uvicorn | async-native, `BackgroundTasks`, Pydantic validation for free |
| LLM runtime | **Ollama** | fully local inference; no keys, no egress |
| Knowledge store | **Neo4j** (Cypher) | relationships *are* the data; a graph DB is the honest model |
| Chat history | **SQLite** + SQLAlchemy | durable log, zero-config, ORM-mapped |
| Client | **Python + Rich** | a polished terminal UI with markdown + spinners |
| Visualization | **React 19 + Vite + react-force-graph-2d** | live force-directed graph on a canvas |

---

## The frontend is not an afterthought

`frontend/src/components/GraphView.jsx` is a custom-rendered force-directed graph:

- Custom canvas node painting with deterministic per-node colors (hashed from the id), contrast-aware label text, and word wrapping
- Tuned d3 force simulation (charge repulsion, link distance, collision) so the graph is readable, not a hairball
- Polls `/graph` every 5s and **merges** state — dragged/pinned node positions survive refreshes instead of snapping back
- Live search that highlights matching nodes and dims the rest, plus directional link coloring toward/away from matches
- Click-to-pin, zoom-to-fit reveal animation, dark/light theme toggle

It's the kind of detail work that signals I care about how the thing actually feels to use.

---

## Running it locally

**Prerequisites:** [Ollama](https://ollama.com), a running Neo4j instance, Python 3.9+, Node 18+.

**1. Backend**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in your Neo4j creds + model names
ollama pull qwen2.5-coder:14b
ollama pull qwen2.5:7b
uvicorn app.main:app --reload
```

**2. Terminal client** (in a second terminal)
```bash
python3 client.py
```

**3. Graph visualization** (optional, in a third terminal)
```bash
cd frontend && npm install && npm run dev
```

**Optional — a `locus` command from anywhere:**
```bash
echo "alias locus='/path/to/venv/bin/python3 /path/to/client.py'" >> ~/.zshrc
source ~/.zshrc
locus
```

Configuration lives in `.env` (see `.env.example`): Neo4j connection, Ollama base URL, and the three model names. Everything is swappable without touching code.

---

## What I'd build next

Honest about where the prototype stops:

- **Semantic retrieval** — the embedding model is wired in but retrieval is currently keyword-based; the natural next step is vector search over node properties for fuzzier recall.
- **Auth + multi-tenancy** — CORS is wide open and there's a single implicit user; both are marked as deliberate "later" in the code.
- **Extraction eval harness** — measuring extraction precision/recall against a labeled set before tuning prompts further.
- **Conflict resolution** — handling contradictory facts over time (temporal validity of edges).

---

## What this project demonstrates

- Designing a multi-service system with a clear data flow, not a monolith script
- Making explicit tradeoffs around latency, cost, and correctness
- Treating LLMs as unreliable components and engineering guardrails around them
- Shipping a real, polished interface on both ends (terminal + web)
- Knowing what's a prototype shortcut and being upfront about it

If you want to talk through any of the decisions above, I'm happy to go deeper on any of them.
