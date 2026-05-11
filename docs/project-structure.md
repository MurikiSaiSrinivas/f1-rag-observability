# Project Structure

> The repo layout, why it's shaped this way, and what gets created in which phase.

## Pattern: monorepo

Multiple related codebases (Python services + Node/Next.js frontend) live in one repository. This is standard in production AI shops because the pieces evolve together — backend changes the API contract, the frontend has to follow, and observability lives across both.

## Full intended layout

```
RAG Observability/
│
├── README.md
├── pyproject.toml                # Python project manifest (uv-managed)
├── uv.lock                       # locked dep versions — reproducible installs
├── .python-version               # pinned Python version
├── .gitignore
├── .env.example                  # template for API keys (real .env is gitignored)
│
├── docs/                         # project documentation
│   ├── project-reference.md      # tech stack, costs, deployment, phases
│   └── project-structure.md      # this file
│
├── data/                         # raw + processed corpus (gitignored — too big)
│   ├── raw/
│   │   ├── ergast/{2020..2025}/  # JSON per season per endpoint
│   │   ├── wikipedia/            # plaintext + wikitext per article
│   │   └── fia/{2020..2025}/     # PDFs + extracted text
│   └── manifest.jsonl            # one row per collected doc
│
├── ingestion/                    # PHASE 1 + 2 — offline corpus building
│   ├── __init__.py
│   ├── collect/                  # Phase 1: fetch raw sources
│   │   ├── ergast.py
│   │   ├── wikipedia.py
│   │   └── fia.py
│   ├── chunk.py                  # Phase 2: split docs into chunks
│   ├── embed.py                  # Phase 2: vector embeddings
│   └── index.py                  # Phase 2: write to Chroma
│
├── rag/                          # PHASE 3 — the runtime RAG pipeline
│   ├── __init__.py               #   (the workload being observed)
│   ├── retriever.py
│   ├── prompts.py
│   └── generator.py
│
├── observability/                # PHASE 4 — the product
│   ├── __init__.py
│   ├── tracing.py                # OpenTelemetry setup + span helpers
│   ├── scoring.py                # RAGAS integration
│   ├── flags.py                  # flag rule engine
│   └── store.py                  # Postgres I/O for scores/flags/feedback
│
├── backend/                      # PHASE 3+ — FastAPI service
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entrypoint
│   ├── routes/
│   │   ├── ask.py                # POST /ask → calls rag/ + observability/
│   │   └── admin.py              # endpoints for the dashboard
│   └── deps.py                   # shared DB sessions etc.
│
├── frontend/                     # PHASE 4+ — Next.js dashboard
│   ├── package.json              # separate Node project, own deps
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── app/
│   ├── components/
│   └── lib/
│
├── infra/                        # PHASE 4+ — ops
│   ├── docker-compose.yml        # Postgres + (maybe) span backend
│   └── migrations/               # Alembic SQL migrations
│
├── scripts/                      # CLI entrypoints that orchestrate modules
│   └── collect.py                # `python scripts/collect.py --source ergast`
│
├── tests/                        # pytest suite (mirrors source layout)
│   ├── ingestion/
│   ├── rag/
│   └── observability/
│
└── .github/
    └── workflows/
        └── ci.yml                # GitHub Actions: lint + tests on push
```

## Design decisions

### 1. Why `ingestion/` is separate from `rag/`
The work splits cleanly in two:
- **Offline / batch:** collect documents and build the index — runs once, occasionally re-runs → `ingestion/`
- **Runtime / online:** receive a question, retrieve, generate → `rag/`

These have totally different shapes (batch jobs vs. request-response). Real production shops always split them.

### 2. Why `observability/` is its own peer, not nested
Observability **wraps** the RAG — cross-cutting concern, not a sub-component. Putting it inside `rag/` would imply it's a feature of the RAG, but the project framing is the opposite: RAG is the *subject being observed* by the observability layer. Folder layout should match the framing.

### 3. Dependency direction
`backend/` imports from `rag/` and `observability/`, never the reverse. The FastAPI service is the thin web layer; logic lives in the packages. Keeping the dependency arrows one-way is what makes the codebase testable and refactorable.

### 4. Frontend is fully separate
Node and Python don't share dependencies. Frontend has its own `package.json`, its own tooling, and deploys to its own host (Vercel in Option B). Only link is the FastAPI URL it hits.

### 5. Flat layout vs. `src/<package>/`
Went flat (packages at repo root) because there are multiple peer packages and the directory names *are* the architecture documentation. `src/` layout is better for single-package installable libraries, which this isn't.

## Naming conventions

- **`ingestion/`** picked over `etl/` (implies transformation we won't really do) and `data/` (collides with raw-files folder).
- **`observability/`** picked over `obs/` (too cryptic) and `monitoring/` (different connotation in industry — monitoring is alerts; observability is "ask any question of your system").

## Phase 1 scope: what gets created now

Only these in Phase 1:
- Root files (`pyproject.toml`, `.python-version`, `.gitignore`, `.env.example`, `README.md`)
- `docs/` (already exists)
- `data/raw/{ergast,wikipedia,fia}/`
- `ingestion/__init__.py` + `ingestion/collect/{ergast,wikipedia,fia}.py`
- `scripts/collect.py`

Everything else (`rag/`, `observability/`, `backend/`, `frontend/`, `infra/`, `tests/`, `.github/`) is created when its phase starts. Empty placeholder folders are noise.

## Dependency direction (visual)

```
                    ┌─────────────┐
                    │   frontend  │  (Next.js, talks HTTP)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   backend   │  (FastAPI, thin web layer)
                    └──────┬──────┘
                           │ imports
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐  ┌──────────┐  ┌──────────────┐
       │   rag    │  │ingestion │  │observability │
       │(runtime) │  │ (offline)│  │   (wraps     │
       │          │  │          │  │  everything) │
       └────┬─────┘  └────┬─────┘  └──────┬───────┘
            │             │               │
            ▼             ▼               ▼
       (Chroma vector store)         (Postgres + span backend)
```
