# Research Vault — Architecture

## 1. Project Overview

Research Vault is a self-hosted research and knowledge management tool. It lets a
single person collect information from the web, save it, extract the readable
article text, annotate it, write their own notes alongside it, organize
everything with tags, and later find it again with full-text search.

**Who it's for:** one person running their own instance (solo researchers,
students, tinkerers, lifelong learners) — not a multi-tenant SaaS product.
Every account is fully isolated (the data model supports multiple `User`
rows), but the intended deployment is "you, on your own machine or server,"
with no team/sharing features. AI/LLM features are **optional**: every AI
capability degrades gracefully (or returns empty results) when no provider
API key is configured, so the app remains fully usable as a plain,
deterministic backend without them.

**Core capabilities:**
- Organize research into **projects** (isolated containers per topic).
- Write and edit **notes** (Markdown-free plain text for now).
- Search the web via a self-hosted **SearXNG** instance and **save** results
  as links.
- Automatically **extract readable article text** from saved links in the
  background (Celery + `readability-lxml`).
- Read saved articles in a distraction-free **reader mode** and **highlight**
  passages with optional annotations.
- Tag notes and links, and click a tag to see everything under it.
- **Full-text search** across notes and links within a project, ranked by
  relevance — optionally **AI-reranked** for semantic relevance.
- **Reading-list statuses** on saved links (`to_read` / `reading` / `done` /
  `archived`) with filtering, independent of tags.
- **Bulk tagging**: add/remove tags across many notes or links in one request.
- Optional **AI assistance** (all backed by one shared AI service with
  multi-provider fallback): explain selected text as a highlight annotation,
  summarise a link's extracted content, generate an ordered research
  **roadmap** for a subject (Redis-cached), and suggest existing tags for new
  content.
- **Markdown export** of a whole project (notes, links, highlights) as a
  downloadable file.
- All of the above through both a **JSON API** (for scripting / external
  tools) and a **server-rendered HTML+HTMX UI** (for day-to-day use), backed
  by the exact same service layer.

---

## 2. Tech Stack

| Layer                     | Technology                              | Role |
|----------------------------|------------------------------------------|------|
| Web framework              | **FastAPI**                              | Async HTTP layer for both the JSON API and the server-rendered UI. |
| ASGI server                | **Uvicorn**                              | Runs the FastAPI app. |
| ORM                        | **SQLAlchemy 2.0** (async + sync)        | Models, querying. Async engine for request handling, sync engine for Celery. |
| Database                   | **PostgreSQL 16**                        | Primary datastore; also provides full-text search (`tsvector`/`tsquery`/GIN) with no extra search infrastructure. |
| Async DB driver             | **asyncpg**                              | Used by the async SQLAlchemy engine (FastAPI request path). |
| Sync DB driver              | **psycopg2**                             | Used by the sync SQLAlchemy engine (Celery task path). |
| Migrations                  | **Alembic**                              | Schema version control. |
| Validation / settings       | **Pydantic v2** / **pydantic-settings**  | Request/response schemas; `.env`-backed `Settings`. |
| Auth                        | **python-jose** (JWT), **passlib[bcrypt]** | Token issuing/verification; password hashing. |
| Background tasks            | **Celery**                               | Runs link content extraction outside the request/response cycle. |
| Task broker/result backend  | **Redis**                                | Celery's broker and result backend; also used directly by the app for roadmap caching and rate limiting. |
| Redis client (app-side)     | **redis-py** (async)                     | Async Redis connection used by the rate limiter (`app/core/rate_limiter.py`) and the roadmap cache (`app/services/roadmap.py`). |
| AI providers                | **huggingface-hub** (`AsyncInferenceClient`) + **httpx** | One shared AI service (`app/services/ai.py`, `call_ai`) with waterfall fallback across OpenRouter → Hugging Face → Groq (any OpenAI-compatible endpoint). Optional per-provider API keys. |
| HTTP client                 | **httpx** (async in the app, sync in the Celery task) | Talks to SearXNG and fetches saved article URLs. |
| Content extraction          | **readability-lxml** + **lxml**          | Strips a fetched page down to its main article text. |
| Web search engine           | **SearXNG** (self-hosted container)      | Privacy-respecting meta search; the app proxies queries to it. |
| Server-rendered UI          | **Jinja2** (`Jinja2Templates`)            | Renders full pages and HTMX fragments from the same service layer as the API. |
| Frontend interactivity      | **HTMX**                                 | Partial page updates (create/edit/delete, tab loading, search) without a JS framework or build step. |
| Styling                     | **Pico.css** (class-less CSS, via CDN)   | Consistent, minimal styling with no build pipeline. |
| Testing                     | **pytest**, **pytest-asyncio**, **aiosqlite**, **httpx.AsyncClient** | Integration tests against the real app; SQLite for fast default runs. |
| Containerization            | **Docker / Docker Compose**              | Runs app, db, redis, searxng, and the Celery worker as separate services. |

There is no separate frontend build (no Node/webpack/React) — the UI is
server-rendered HTML enhanced with HTMX, by design (see §4).

---

## 3. High-Level System Diagram (in words)

**Docker Compose services:**
- `app` — the FastAPI application (Uvicorn), serves *both* `/api/v1/*` JSON
  endpoints and the HTML/HTMX UI on the same port (8000).
- `db` — PostgreSQL 16, with a healthcheck gating the other services.
- `redis` — Celery's broker and result backend, *and* the app-side store for
  roadmap caching and fixed-window rate limiting (both via the async
  `redis_client` in `app/core/redis.py`).
- `searxng` — a self-hosted SearXNG meta search engine, queried over HTTP by
  `app`.
- `celery_worker` — the same application image as `app`, but running
  `celery -A app.tasks.celery_app worker` instead of Uvicorn. It shares the
  Postgres database with `app` but talks to it through a *separate, sync*
  connection (see §4 and §8).

**Note on the reverse proxy:** the current `docker-compose.yml` does **not**
include an Nginx (or any TLS-terminating) layer — the browser talks directly
to Uvicorn on port 8000. For a real internet-facing deployment you'd typically
put Nginx/Caddy/Traefik in front of `app` for TLS termination, static-asset
caching, and to hide the `--reload` dev server; that's a recommended addition
for production hardening, not something already in this stack today. The
diagram below reflects the actual current topology.

**Request flow — a page view / API call:**
```

Browser
  │  HTTP (cookie or Bearer token)
  ▼
app (Uvicorn/FastAPI)
  ├─ /api/v1/*        → JSON API routers   ─┐
  └─ /, /projects/...  → HTML/HTMX UI routers ┤→ same Service Layer
                                              │   (app/services/*)
                                              ▼
                                     SQLAlchemy AsyncSession
                                              │
                                              ▼
                                          PostgreSQL (db)

```

**Request flow — web search:**

```

Browser → app (search form/endpoint) → httpx (async) → searxng container
                                                          │
                                     JSON results  ◄──────┘
Browser ◄── rendered results (HTML fragment or JSON)

```

**Request flow — saving a link (background extraction):**

```

Browser → app: POST .../links  (or .../links/save for HTMX)
              │
              ├─ link_service.create_link()
              │     ├─ INSERT saved_links row (status = "pending")
              │     └─ extract_link_content.delay(link_id)  ──► Redis (broker)
              │
              ▼
        Response returned immediately (link shown as "Pending")

Redis → celery_worker picks up the task
              │
              ├─ sync SQLAlchemy session (SessionLocal)
              ├─ httpx.Client → fetch the URL
              ├─ readability-lxml → extract article text
              └─ UPDATE saved_links (extracted_content, status)
                     │
                     ▼
              PostgreSQL (same db as app)

Browser (HTMX) polls/re-fetches the link item a few seconds later and
sees the updated status ("Completed"/"Failed") and content.

```

---

## 4. Key Design Decisions & Rationale

### Why async FastAPI + sync Celery workers
Request handling is I/O-bound (many concurrent DB queries, occasional calls
out to SearXNG), so an async event loop lets one Uvicorn process serve many
concurrent requests without a thread per connection — that's what FastAPI's
async routes and the async SQLAlchemy engine (`asyncpg`) are for.

Celery, however, runs each task in its own OS process/thread outside any
asyncio event loop (its default prefork worker model). A single extraction
task is inherently sequential and blocking anyway — fetch one URL, parse the
HTML, write one row — so there's no concurrency to gain from async there, and
bridging asyncio into Celery's worker model (event loop lifecycle per task,
sharing pooled async connections across forked processes) adds real
complexity for no benefit. So the task uses a plain **sync** SQLAlchemy
engine/session (`SessionLocal` / `sync_engine`, via `psycopg2`) and a
**sync** `httpx.Client`. Both the async and sync engines point at the same
Postgres database, just through different drivers/URLs
(`DATABASE_URL` vs `DATABASE_URL_SYNC`).

### Why PostgreSQL full-text search instead of Elasticsearch
For a single-user, self-hosted tool, running a second search cluster (and
keeping it in sync with Postgres) is disproportionate operational overhead.
Postgres's built-in `tsvector`/`tsquery`/GIN-index full-text search is more
than adequate at the scale of one person's notes and saved links, keeps the
whole stack to "one real database," and avoids a second reindexing pipeline
to maintain. `search_collected()` runs a single `UNION ALL` query with
`ts_rank_cd` for relevance ordering across `notes` and `saved_links` — good
enough ranking without extra infrastructure. If the dataset ever grew to
millions of documents across many users, Elasticsearch/OpenSearch would be
the right trade-off; that's not this tool's use case.

### Why tags, not folders
Notes and links routinely relate to more than one topic at once (a link can
be `python`, `async`, *and* `tutorial` simultaneously). A folder hierarchy
forces a single parent and encourages premature categorization; tags are a
flat many-to-many relationship (`NoteTag`/`LinkTag`) scoped per project
(`UniqueConstraint("project_id", "name")`), so organization stays flexible
and cheap to change. The "click a tag to filter" UI (`GET
/projects/{id}/tags/{tag_id}/items`) gives folder-like browsing *on top of*
tags without giving up the many-to-many flexibility.

### Why JWT in an httpOnly cookie for the UI, but Bearer token also supported
The same JWT format and verification logic (`decode_access_token`) serves
both surfaces — there's exactly one place tokens are minted
(`issue_token_for_user`) and one place they're decoded.

- The **HTML UI** sets the token in an **httpOnly** cookie
  (`app/api/v1/auth.py::_set_auth_cookie`) so plain page navigations and
  HTMX requests are authenticated automatically, without any client-side JS
  wiring headers on every request — and `httpOnly` means page JavaScript
  can't read the token, which limits the blast radius of an XSS bug (the
  token can't be exfiltrated by a malicious script, only used same-origin).
- The **JSON API** still accepts a normal `Authorization: Bearer <token>`
  header (`get_current_user` / `OAuth2PasswordBearer`), so it remains a
  conventional, stateless API usable from `curl`, Swagger UI, or any
  external client — not something that only works from inside the bundled
  browser UI.

Two small FastAPI dependencies exist for this
(`get_current_user` vs `get_current_user_from_cookie`), but both delegate to
one shared `_resolve_user_from_token()` helper in
`app/core/dependencies.py`, so the actual token-validation logic is not
duplicated — only the *place the token is read from* differs.

### Why extracted content is stored as plain text — and a correction on rendering
`app/tasks/extraction.py` runs `readability-lxml` to isolate the article's
main HTML, then immediately strips it down with
`fromstring(raw_html).text_content()` before it's ever written to the
database. **The stored `extracted_content` column is plain text, not HTML.**

The reasoning: the source of that content is an arbitrary, untrusted
third-party web page. Storing raw (or even "sanitized") HTML from the open
web and re-rendering it inside the app's own pages is a much bigger attack
surface (stored XSS via a malicious saved article) for very little payoff in
a plain-text reading experience. Plain text also keeps full-text search
simpler (no tag-stripping needed at query time) and keeps the reader view
fast and predictable.

One correction versus how this is sometimes phrased: the reader-mode and
"view content" templates render `extracted_content` through Jinja's **default
auto-escaping** (`{{ link.extracted_content }}` inside a `<div>`/`<pre>`),
**not** with the `|safe` filter. That's intentional and consistent with the
"plain text, not HTML" decision above — using `|safe` would only make sense
if the field actually contained trusted markup, which it deliberately does
not. If a future version wants basic formatting (paragraphs, headings) in
the reader view, the right fix is to store a small amount of *sanitized*
HTML (e.g. via `bleach`) at extraction time, not to mark the current
plain-text field as safe.

### Why highlight offsets are integer character positions
`Highlight.start_offset` / `Highlight.end_offset` are plain integers over
the character stream of `extracted_content`. This is the simplest possible
representation: it doesn't depend on DOM structure, survives the content
being re-rendered differently later, and is trivial to store/index — no need
for a DOM-path-based anchoring scheme.

**Current implementation status, stated plainly:** the reader page's
selection-to-highlight flow (`links/read.html`) currently sends
`start_offset = 0` and `end_offset = text.length` as placeholder values along
with the selected text itself — it does **not** yet walk the browser's
`Selection`/`Range` API against the rendered article to compute the text's
*true* position within `extracted_content`. This matches the original
scope ("we can skip complex text offset validation for now") but it means
today the offsets are not reliable for re-locating a highlight precisely
within the source text; only `selected_text` (and the optional annotation)
are meaningful right now. Implementing real range→character-offset mapping
(walking text nodes under `#reader-article` to find the absolute offset of
the selection anchor) is the natural next step and is isolated to the
client-side JS in `read.html` — no schema or API change would be required.

### Why one shared AI service with provider waterfall, not per-feature clients
Every AI-backed feature (explain, summarise, roadmap, tag suggestions,
semantic rerank) goes through a single `call_ai()` function in
`app/services/ai.py`. It builds a provider list from whichever optional API
keys are configured (`OPENROUTER_API_KEY`, `HF_API_KEY`, `GROQ_API_KEY`) and
tries them in order — OpenRouter first, then Hugging Face's
`AsyncInferenceClient`, then Groq — falling back to the next provider on any
failure. This gives three properties for free: features never duplicate
client/auth/parsing code; regional blocking of one provider degrades to the
next instead of failing the request; and with *no* keys set, `call_ai` raises
a clear `AIError` that each endpoint maps to its own graceful degradation
(502, empty suggestions, or full-text-only search order). Shared response
parsing helpers (`extract_json_array` / `parse_json_array`) live here too,
since every prompt asks for raw JSON arrays and LLMs wrap them in prose or
markdown fences unpredictably.

### Why "semantic search" is AI reranking, not vector search
`search_semantic()` (`app/services/semantic_search.py`) takes the top 10
candidates from the existing Postgres full-text search and makes **one** AI
call asking the model to return them reordered as a JSON array of IDs. It is
deliberately *not* an embedding/vector store: nothing becomes retrievable
that full-text search wouldn't already find. For one person's library this
avoids an entire embedding pipeline + vector index (and keeping it in sync),
while still fixing the classic FTS weakness — lexical matches ranked without
any notion of *meaning*. Failure handling is total: if the AI call fails or
returns unparsable JSON, the full-text ordering is returned unchanged (the
endpoint always answers 200). Model-invented IDs are ignored and omitted
candidates keep their original order at the end, so reranking can never drop
a result.

### Why rate limiting is a Redis fixed window that fails open
`app/core/rate_limiter.py` implements a reusable dependency factory
(`create_rate_limit_dependency`) rather than per-endpoint middleware: keys are
scoped per caller (`user:{id}` when authenticated via the optional-auth
dependency, `ip:{host}` otherwise), bucketed into wall-clock windows with
`INCR` + `EXPIRE`. Two instances exist: a shared **AI budget** (`ai_rate_limit`)
covering roadmap, summarise, explain, suggest-tags, and search-semantic (so
one user can't multiply their quota across endpoints), and an IP-keyed
**auth budget** (`auth_rate_limit`) as brute-force protection on register/
login. When Redis is unavailable, behaviour follows `RATE_LIMITER_FAIL_OPEN`
(default `true`: log and allow, so a Redis outage never takes the app down;
`false`: fail closed with `503`). Quota headers (`X-RateLimit-Limit`,
`X-RateLimit-Remaining`, `Retry-After` on 429) are always set so callers can
see remaining quota before hitting it.

---

## 5. Data Models

All tables use UUID primary keys and `created_at`/`updated_at` timestamps
where relevant. Ownership always flows: `User → Project → {Note, SavedLink,
Tag}`.

| Table         | Purpose | Key relationships |
|---------------|---------|--------------------|
| **users**       | One row per account; stores email + bcrypt password hash. | Owns many `projects` (cascade delete). |
| **projects**    | An isolated container for one research topic, owned by exactly one user. | Belongs to a `user`; owns many `notes`, `saved_links`, and `tags` (all cascade delete). |
| **notes**       | A free-text note within a project. | Belongs to a `project`. Optionally references one `saved_links` row via `source_link_id` (nullable, `ON DELETE SET NULL` — deleting the link detaches the note rather than deleting it). Many-to-many with `tags` through `note_tags`. |
| **saved_links**  | A URL saved from web search (or added directly), plus its extraction state, extracted article text, AI summary, and reading-list status. | Belongs to a `project`. Many-to-many with `tags` through `link_tags`. Owns many `highlights` (cascade delete). `extraction_status` is one of `pending` / `completed` / `failed`; `status` is one of `to_read` / `reading` / `done` / `archived` (defaults `to_read`, independent of tags); `summary` is a nullable AI-generated summary written by the summarisation endpoint. |
| **tags**        | A short label, unique per project (`project_id` + `name`). | Belongs to a `project`. Many-to-many with both `notes` and `saved_links`. |
| **note_tags**    | Association table (composite PK: `note_id`, `tag_id`). | Links one `note` to one `tag`. |
| **link_tags**    | Association table (composite PK: `link_id`, `tag_id`). | Links one `saved_link` to one `tag`. |
| **highlights**   | A user-selected excerpt of a saved link's extracted content, with an optional annotation. | Belongs to a `saved_link` (`ON DELETE CASCADE` — deleting the link deletes its highlights). Stores `selected_text`, `annotation` (nullable), `start_offset`/`end_offset` (see §4 for their current limitations). |

Full-text search does not add a new table — it queries `notes` and
`saved_links` directly via `to_tsvector(...)` expressions (backed by GIN
indexes created in an Alembic migration), rather than maintaining a
duplicated search index table.

---

## 6. API Design

**Versioning:** the entire JSON API is mounted under `/api/v1`
(`app/main.py`), grouped into routers: `auth`, `projects`,
`projects/{project_id}/notes`, `projects/{project_id}/tags`, links/search
endpoints nested under `projects/{project_id}`, and a project-independent
`roadmap` router at `/api/v1/roadmap`. The server-rendered UI lives
at unversioned, unprefixed paths (`/`, `/login`, `/dashboard`,
`/projects/{project_id}`, ...) — it's not a stable external contract the way
the JSON API is, so it doesn't need its own version namespace, and keeping it
out of `/api/v1` also keeps it out of the OpenAPI schema
(`include_in_schema=False` on both UI routers).

**Auth flow:**
1. `POST /api/v1/auth/register` or `/login` validates credentials against
   `services/auth.py`, mints a JWT (`create_access_token`), returns it in the
   JSON body **and** sets it as an httpOnly cookie.
2. Subsequent JSON API calls authenticate via `Authorization: Bearer <token>`
   (`get_current_user`); subsequent UI page loads authenticate via the
   `access_token` cookie (`get_current_user_from_cookie`). Both dependencies
   decode the same JWT format and resolve to the same `User` row.

**User isolation / scoping:** every resource beneath a project is reached
through a **path-param ownership dependency** —
`get_current_project` (API) / `get_current_project_from_cookie` (UI) —
which resolves `project_id` from the URL, looks it up, and checks
`project.user_id == current_user.id`. This one dependency, reused on every
nested router, gives every note/tag/link/search endpoint automatic
"this project isn't yours" protection for free, with a deliberate
distinction between:
- **404 Not Found** — the project doesn't exist at all, and
- **403 Forbidden** — the project exists but belongs to someone else.

Because every query inside the service layer additionally filters by
`project_id` (e.g. `note_service.get_note(..., project_id=..., note_id=...)`),
a user cannot retrieve another user's data even by guessing a valid note/tag/
link UUID — the row simply won't match the `WHERE project_id = ...` clause
and looks identical to "not found."

**Endpoint patterns:** conventional REST — `POST` create (`201`), `GET`
list/detail, `PUT` partial-ish update (body validated via a schema whose
fields default to optional / `exclude_unset=True`), `DELETE` (`204`).
Association actions (attach/detach a tag) are modeled as sub-resources:
`POST/DELETE /notes/{note_id}/tags[/{tag_id}]`,
`POST/DELETE /links/{link_id}/tags[/{tag_id}]`, plus a project-wide
`POST /links/bulk-tags` for applying/removing tags across many notes or
links at once. Cross-cutting actions that aren't pure CRUD get their own
verbs under the same nested prefix: `POST /projects/{id}/search` (proxy a
SearXNG query), `GET /projects/{id}/search-collected` (full-text search),
`POST /projects/{id}/search-semantic` (full-text search + AI rerank),
`POST /projects/{id}/suggest-tags`, `POST .../links/{link_id}/explain`,
`POST .../links/{link_id}/summarise`, `PATCH .../links/{link_id}/status`,
and `GET /projects/{id}/export/markdown`.

**Rate limiting:** all AI-backed endpoints share one Redis fixed-window
budget (`ai_rate_limit`), and register/login have an IP-keyed budget
(`auth_rate_limit`) — see §4. Exceeding a limit returns `429` with
`Retry-After`; if the limiter's Redis is down, `RATE_LIMITER_FAIL_OPEN`
decides between allowing the request (default) or `503`.

**API vs UI symmetry:** the UI routers (`app/api/ui.py`,
`app/api/ui_project.py`) intentionally mirror this same
resource/ownership/service-call structure, just returning rendered
HTML/HTMX fragments instead of JSON — see §7 for how that avoids duplicating
business logic.

---

## 7. Folder Structure

```

app/
├── main.py                 # App factory: mounts API + UI routers, lifespan
│                            # (create_all for dev convenience), mapper config
├── core/
│   ├── config.py            # Settings (pydantic-settings, reads .env)
│   ├── security.py          # JWT issue/decode, bcrypt password hashing
│   ├── dependencies.py      # Auth + project-ownership dependencies —
│   │                        # both header-based (API) and cookie-based (UI),
│   │                        # sharing one token-resolution helper; also
│   │                        # combined (header-or-cookie) and optional-auth
│   │                        # variants used by export and rate limiting
│   ├── rate_limiter.py        # Redis fixed-window rate limiter dependency
│   │                          # factory; `ai_rate_limit` and `auth_rate_limit`
│   ├── redis.py               # Shared async Redis client (app-side)
│   └── templates.py         # Single shared Jinja2Templates instance
├── db/
│   ├── base.py               # SQLAlchemy DeclarativeBase
│   └── session.py            # Async engine/session (FastAPI) AND
│                              # sync engine/session (Celery) — same DB,
│                              # two drivers
├── models/                   # One SQLAlchemy ORM class per table.
│                              # __init__.py imports all of them so the
│                              # mapper registry is complete before any
│                              # query runs, and so Alembic autogenerate
│                              # sees every table.
├── schemas/                  # Pydantic request/response models, one file
│                              # per resource (mirrors models/ roughly)
├── services/                  # ALL business logic. Pure async functions
│                              # taking an AsyncSession + explicit kwargs;
│                              # no HTTP/FastAPI concerns in here at all.
│                              # Includes the AI-backed services (ai.py =
│                              # shared `call_ai` + provider waterfall +
│                              # JSON parsing; roadmap.py, summarisation.py,
│                              # tag_suggestion.py, semantic_search.py) and
│                              # bulk_tags.py / export.py. Both api/v1/*.py
│                              # and api/ui*.py import from here — this is
│                              # the one place logic lives, so it's never
│                              # duplicated between the JSON API and the
│                              # HTML UI.
├── api/
│   ├── v1/                   # JSON API routers — thin: validate the
│   │                          # request via a schema, call a service
│   │                          # function, translate service exceptions
│   │                          # (NotFoundError, AlreadyExistsError, ...)
│   │                          # into the right HTTPException.
│   │                          # roadmap.py is project-independent
│   │                          # (`POST /api/v1/roadmap`).
│   ├── ui.py                  # HTML pages: /, /login, /register,
│   │                          # /dashboard, /logout
│   └── ui_project.py          # HTML/HTMX routes for everything under
│                              # /projects/{id}/...: notes, tags, links,
│                              # web search, saved-link management, reader
│                              # mode, highlights, tag filtering, manual
│                              # re-extraction
├── templates/
│   ├── base.html              # Layout: Pico.css + HTMX from CDN, nav,
│   │                          # shared styling
│   ├── *.html                 # Full pages (login, register, dashboard,
│   │                          # project_detail, links/read.html, ...)
│   └── {notes,tags,links,search,partials}/_*.html
│                              # Fragment templates — no /base
│                              # inheritance, returned directly as HTMX
│                              # swap targets
└── tasks/
    ├── celery_app.py          # Celery app config (broker/backend = Redis)
    └── extraction.py          # The one background task: fetch → extract
                                # → persist, using the sync engine

alembic/
├── env.py                     # Reads DATABASE_URL_FOR_ALEMBIC, imports
│                              # app.models so target_metadata is complete
└── versions/                  # Linear migration history

tests/
├── conftest.py                 # Patches engines to SQLite before app
│                              # import; per-test DB create/drop; Celery
│                              # eager mode; make_user + client fixtures
└── test_*.py                  # Roughly one file per feature/router

searxng/settings.yml            # Config for the bundled SearXNG container
docker-compose.yml, Dockerfile, requirements.txt,
alembic.ini, pytest.ini, .env.example

```

The consistent rule throughout: **services/ is the only place with business
logic**; both `api/v1/*` and `api/ui*.py` are thin adapters over it that
differ only in how they take input (JSON body vs form fields) and how they
produce output (Pydantic-serialized JSON vs a rendered template).

---

## 8. Background Tasks

The only background task today is `extract_link_content` (`app/tasks/
extraction.py`), registered on the shared `celery_app`
(`app/tasks/celery_app.py`, broker = Redis).

**Dispatch points:**
- `link_service.create_link()` calls `.delay(str(link.id))` immediately
  after inserting the new `saved_links` row (status starts `pending`).
- `link_service.trigger_extraction()` (manual "Re-extract" button) resets
  `extraction_status` back to `pending` and calls `.delay()` again — used
  both to retry a failed extraction and to simply refresh already-completed
  content.

**What the task does, step by step:**
1. Opens a plain **sync** SQLAlchemy session via `SessionLocal` (the sync
   engine defined in `app/db/session.py`) — deliberately *not* the async
   engine, since Celery's worker process has no asyncio event loop running
   (see §4 for the full rationale).
2. Loads the `SavedLink` row by ID; if it's gone, logs and returns
   (defensive — the link could theoretically be deleted between dispatch and
   execution).
3. Fetches the URL with a **sync** `httpx.Client` (15s timeout, follows
   redirects, single fixed `User-Agent`).
4. Runs `readability.Document(...).summary()` to isolate the article HTML,
   then `lxml.html.fromstring(...).text_content()` to reduce it to plain
   text (see §4 on why plain text, not HTML, is stored).
5. On success: sets `extracted_content` and `extraction_status =
   completed`. On *any* exception (network error, HTTP error status,
   parsing failure): sets `extraction_status = failed` and logs the
   exception — the task always resolves to a terminal status, so a link
   never gets stuck showing "pending" forever because of a page that timed
   out or 404'd.
6. Commits. A separate `try/except` around the whole body ensures a
   genuine DB-commit failure rolls back and re-raises, so Celery's normal
   retry machinery can see it (as distinct from a *content-fetch* failure,
   which is captured and recorded as `failed` rather than raised).

The UI surfaces this asynchronously: after saving a link, HTMX polls the
single-link fragment endpoint (`GET /projects/{id}/links/{link_id}`) every
few seconds via `hx-trigger="load delay:3s"` while status is `pending`, so
the "Pending → Completed/Failed" transition shows up without a manual page
refresh, and the client-side "Re-extract" button is disabled while a task is
in flight to avoid trivially queueing duplicate work (no server-side
locking — acceptable for a single-user tool per the original MVP scope).

---

## 9. Testing Strategy

**Default setup (`tests/conftest.py`):** before the app is even imported,
the async and sync engines are monkey-patched to point at SQLite
(`sqlite+aiosqlite:///:memory:` and `sqlite:///:memory:` respectively). This
keeps the default `pytest` run fast, hermetic, and independent of a running
Postgres/Redis — no docker services required to run the suite. A fresh
schema (`Base.metadata.create_all`) is created and dropped around **every
test function**, so tests never leak state into each other. Celery is
configured with `task_always_eager=True` / `task_eager_propagates=True`, so
`.delay()` calls execute synchronously in-process during tests instead of
requiring a live Redis broker.

**Integration tests (the large majority of the suite):** real
`httpx.AsyncClient` + `ASGITransport` against the actual FastAPI `app`,
exercising real routers → real services → the real (in-memory) database.
This is deliberate: it catches wiring bugs (a service function returning the
wrong shape, a route forgetting the ownership dependency, a template
referencing an undefined variable) that pure unit tests of the service layer
alone would miss. Coverage includes: auth (register/login/token
validation), project CRUD + ownership isolation, note CRUD + tag
attach/detach, tag CRUD + duplicate-name handling, link save/list/delete +
tag attach/detach, the full-text search endpoint, and the entire
server-rendered UI surface (page loads, HTMX fragment endpoints, form
submissions, delete-via-empty-200-body behavior, ownership redirects/403s).
A `make_user` fixture registers a fresh user through the *real*
`/api/v1/auth/register` endpoint per call, so ownership/isolation tests use
genuinely distinct, realistically-created users rather than hand-inserted
rows.

**Narrower unit-style tests:** `tests/test_extraction.py` tests the Celery
task in isolation, using its own sync SQLite session fixture and mocking
`httpx.Client` / `readability.Document` — this covers the task's three
outcome branches (success, network error, parsing error) without ever
making a real network call.

**Mocking external services:** `search_searxng` (and, in the UI, the
identically-named import inside `app/api/ui_project.py`) is patched with
`unittest.mock.AsyncMock` in tests, so the suite never depends on a live
SearXNG container and can assert on both the happy path and an upstream
502.

**A known, explicitly-flagged limitation:** the full-text search tests
(`test_collected_search.py`) rely on Postgres-only SQL (`to_tsvector`,
`plainto_tsquery`, `ts_rank_cd`), which **SQLite does not support**. These
tests only actually exercise real matching/ranking behavior when run against
a real Postgres backend — e.g. `docker compose exec app pytest` with
`TEST_DATABASE_URL` / `TEST_DATABASE_URL_SYNC` pointed at the `db` service,
per the override hooks already present in `conftest.py`. Under the default
in-memory SQLite run they would fail outright (`to_tsvector` doesn't exist as
a SQLite function) — this is called out here rather than left as a surprise;
running the full-text-search tests against Postgres before merging changes
to that feature is a manual step, not something CI enforces automatically
today.

**Authorization is tested at every layer**, consistently distinguishing
`404` (resource doesn't exist) from `403` (exists, but isn't yours) for
projects, notes, tags, links, and highlights alike.

---

## 10. Deployment / Running

**Prerequisites:** Docker and Docker Compose. Nothing else needs to be
installed locally.

**Steps:**
```bash
git clone <repo>
cd research-vault
cp .env.example .env        # then edit JWT_SECRET etc. for real deployments
docker compose up -d
docker compose exec app alembic upgrade head
```

**Services started by `docker compose up`:**

| Service           | Image / build            | Purpose                                                                      |
| ----------------- | ------------------------ | ---------------------------------------------------------------------------- |
| `app`           | built from`Dockerfile` | FastAPI + Uvicorn, serves API and UI on`:8000`                             |
| `db`            | `postgres:16`          | Primary database, port`5430` on the host                                   |
| `redis`         | `redis:7-alpine`       | Celery broker/result backend, port`6378` on the host                       |
| `searxng`       | `searxng/searxng`      | Self-hosted search engine, port`8080` on the host                          |
| `celery_worker` | same build as`app`     | Runs`celery -A app.tasks.celery_app worker`; depends on `db` + `redis` |

`app` and `celery_worker` both wait on `db`'s healthcheck
(`pg_isready`) before starting.

**Environment variables** (see `.env.example`):

| Variable                                                    | Purpose                                                                                                         |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                                            | Async connection string (`postgresql+asyncpg://...`), used by FastAPI request handling.                       |
| `DATABASE_URL_SYNC`                                       | Sync connection string (`postgresql://...`), used by Celery tasks and Alembic.                                |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Passed into the`db` container to initialize Postgres.                                                         |
| `REDIS_URL`                                               | Celery broker/backend URL.                                                                                      |
| `SEARXNG_URL`                                             | Internal URL the app uses to reach the`searxng` container.                                                    |
| `JWT_SECRET`                                              | Signing secret for access tokens —**must** be changed from the placeholder for any non-local deployment. |
| `JWT_ALGORITHM`                                           | Defaults to`HS256`.                                                                                           |
| `JWT_EXPIRE_MINUTES`                                      | Token / cookie lifetime.                                                                                        |
| `APP_ENV`                                                 | Free-form environment marker (`development`, etc.).                                                           |
| `OPENROUTER_API_KEY` / `HF_API_KEY` / `GROQ_API_KEY` / `GEMINI_API_KEY` | Optional AI provider keys. The AI waterfall uses whichever are set (in that order); with none set, AI features fail gracefully. |
| `ROADMAP_CACHE_TTL_SECONDS`                               | Redis TTL for cached roadmaps (default `3600`).                                                                |
| `AI_RATE_LIMIT_MAX_REQUESTS` / `AI_RATE_LIMIT_WINDOW_SECONDS` | Shared fixed-window budget for all AI endpoints (defaults `10` / `60`).                                    |
| `AUTH_RATE_LIMIT_MAX_REQUESTS` / `AUTH_RATE_LIMIT_WINDOW_SECONDS` | IP-keyed fixed-window budget for register/login (defaults `20` / `300`).                                |
| `RATE_LIMITER_FAIL_OPEN`                                  | `true` (default) allows requests when Redis is down; `false` returns `503`.                                   |

**Migrations:** `alembic upgrade head` inside the `app` container applies
all schema changes, including the full-text-search GIN indexes, the
`notes.source_link_id` / `highlights` migration, the `saved_links.summary`
column (AI summaries), and the `saved_links.status` column (reading-list
statuses). Note that `app/main.py`'s
`lifespan` also calls `Base.metadata.create_all` on startup as a dev
convenience (so a brand-new empty database "just works" without running
Alembic first); this is idempotent and harmless alongside real migrations,
but **Alembic remains the source of truth for schema evolution** — always
run `alembic upgrade head` after pulling changes that touch `app/models/`,
rather than relying on `create_all` to pick up column/index changes on an
existing database (it won't — `create_all` only creates tables that don't
exist yet, it never alters existing ones).

**Accessing the app:**

- UI: `http://localhost:8000/`
- Interactive API docs (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

**Running tests:**

```bash
docker compose exec app pytest                      # fast, SQLite-backed
# or, for full-text-search coverage against real Postgres:
docker compose exec app env \
  TEST_DATABASE_URL=postgresql+asyncpg://vault:vault@db:5432/researchvault_test \
  TEST_DATABASE_URL_SYNC=postgresql://vault:vault@db:5432/researchvault_test \
  pytest
```
