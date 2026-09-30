![Stars](https://img.shields.io/github/stars/AminodinAkbari/Research-vault)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

# Research Vault

A self-hosted research and knowledge management platform you can run on your own machine. Collect web research, extract and read articles distraction-free, highlight passages, take notes — with **optional** one-shot AI helpers (summaries, roadmaps, semantic search) that stay out of the way when unconfigured.

> ⚠️ **Active development** – new features land every few days. Check back often or star the repo to follow along.

---

⭐ If you find this useful, please consider starring the repo!

## What is this?

Research Vault helps you collect, organize, and rediscover information from the web and your own notes. Think of it as a personal knowledge base for solo researchers, tinkerers, and lifelong learners.

**It is NOT**

- an AI chatbot or LLM wrapper (AI features are one-shot helpers, never conversation)
- a SaaS product
- a complex multi‑user collaboration tool

**It IS**

- a self-hosted research tool you fully control
- a showcase of modern backend engineering (FastAPI, async Python, clean architecture)
- completely free and open source

---

## Features (so far)

All of the following are implemented and tested:

- **User authentication** – register, login, JWT-protected endpoints
- **Research projects** – create isolated containers for different topics
- **Notes** – write plain‑text notes inside any project (full CRUD)
- **Tags** – per-project tags on notes *and* links, plus **bulk tag operations**
- **Web search & link saving** – search via self-hosted SearXNG, save results with automatic background article extraction
- **Reader mode & highlights** – distraction-free reading with colored highlights and annotations
- **Reading-list statuses** – `to_read` / `reading` / `done` / `archived` workflow states with filtering
- **Full-text search** – PostgreSQL FTS across notes and links, ranked by relevance
- **Markdown export** – compile a whole project (notes, links, highlights) into one downloadable `.md` file
- **AI-powered helpers** *(optional — set any provider API key to enable)*:
  - **Research Kickstart** – type a topic, get an AI-generated learning roadmap with search keywords (Redis-cached)
  - **Summarise this article** – short AI summary stored on the saved link
  - **“Explain this” highlight** – select a passage in the reader, get a concise explanation saved as an annotation
  - **Tag suggestions** – AI picks up to 3 tags from your existing vocabulary
  - **Semantic search** – full-text results reranked by meaning; falls back to plain FTS when AI is unavailable
- **Rate limiting** – Redis-backed fixed-window limits on auth (brute-force protection) and all AI endpoints
- **User isolation** – every request is scoped to the logged-in user
- **Full test suite** – async integration tests for all endpoints
- **Docker Compose** – one command to start the whole stack

AI providers work via a waterfall fallback: set any of `OPENROUTER_API_KEY`, `HF_API_KEY`, or `GROQ_API_KEY` in your `.env`. With none set, the app works perfectly fine without any AI features.

## Coming soon

These are planned or under active consideration:

- **Full‑text PDF / EPUB extraction** – expand the extraction pipeline beyond web pages.
- **Progressive Web App (PWA)** – work offline on mobile, sync when back online.
- **New frontend** – a modern JS frontend to replace the server-rendered HTMX UI (see `UI-SPEC.md`).

---

## Tech Stack

| Layer            | Technology                                                        |
| ---------------- | ----------------------------------------------------------------- |
| API framework    | FastAPI (async)                                                   |
| Database         | PostgreSQL 16 + SQLAlchemy 2.0 (async)                            |
| Migrations       | Alembic                                                           |
| Validation       | Pydantic v2                                                       |
| Caching / broker / rate limiting | Redis                                             |
| Background tasks | Celery (using Redis as broker)                                    |
| AI providers     | Hugging Face Inference Client, OpenRouter, Groq (optional keys)   |
| Search engine    | SearXNG (self‑hosted)                                            |
| UI               | Server-rendered Jinja2 + HTMX + Pico.css                          |
| Containerization | Docker Compose                                                    |
| Auth             | JWT via `python-jose`, password hashing with `passlib[bcrypt]`    |

---

## Getting Started

You need Docker and Docker Compose installed. That's it.

### 1. Clone the repo

```bash
git clone https://github.com/aminodinakbari/research-vault.git
cd research-vault
```

### 2. Set up environment

```bash
cp .env.example .env
# optional: add one AI provider key (OPENROUTER_API_KEY / HF_API_KEY / GROQ_API_KEY)
```

### 3. Start everything

```bash
docker compose up -d
```

This launches:

- The FastAPI app (on http://localhost:8000)
- PostgreSQL
- Redis
- SearXNG (web search)
- A Celery worker (for background extraction tasks)

### 4. Run database migrations

```bash
docker compose exec app alembic upgrade head
```

### 5. Open the interactive API docs

Go to http://localhost:8000/docs.
You can register a user, create projects, write notes, and explore every endpoint directly from the browser.

---

## Frontend development (Next.js port)

A Next.js 14 (App Router + Tailwind) port of the HTMX UI lives in `frontend/`.
It is a separate Node build: the backend keeps serving the original HTMX UI on
http://localhost:8000, so both UIs run side by side.

### Run it

```bash
# 1. backend up (from the repo root)
docker compose up -d

# 2. frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

### Environment

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | Backend API location. The client fetches `/api/...` with relative URLs; Next.js rewrites proxy them to this backend. Restart `npm run dev` after editing `.env.local`. |

### CORS

The frontend runs on port 3000 and the API on port 8000 (different origins):

- **Default path:** API calls use relative URLs and are proxied by the rewrites
  in `frontend/next.config.js` (`/api/:path*` and `/logout` → `http://localhost:8000`),
  so they are same-origin and need no CORS.
- **Direct `:8000` calls** from the browser (e.g. the session probe in
  `frontend/src/hooks/useAuth.ts`) are cross-origin and rely on the explicit
  allowlist in `app/main.py`:

```python
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

Serve the frontend from another host/port and add that origin to this list.
Because auth is an httpOnly cookie, every request uses `credentials: 'include'`
and the API uses `allow_credentials=True` — an `allow_origins=["*"]` wildcard
is not an option. A missing origin shows up as a CORS error in the browser
console; see the troubleshooting table in
[`specs/001-nextjs-frontend/quickstart.md`](specs/001-nextjs-frontend/quickstart.md).

### Checks

```bash
cd frontend
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run test        # Vitest unit tests
npm run test:e2e    # Playwright (backend must be running)
npm run build       # production build
```

---

## Usage (via Swagger)

Once the app is running:

1. `POST /api/v1/auth/register` to create an account.
2. `POST /api/v1/auth/login` to get a JWT token, then click *Authorize* in Swagger and paste it.
3. Create a project with `POST /api/v1/projects`.
4. Search the web with `POST /api/v1/projects/{id}/search` and save results as links.
5. Write notes (`.../notes`), manage tags (`.../tags`), try AI endpoints like `/roadmap` or `.../links/{link_id}/summarise`.

For full endpoint documentation see [`API-SPEC.md`](API-SPEC.md); architecture details are in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Network & Proxy Configuration (Regional Restrictions for iraninan users and other countries)

Some AI providers (such as OpenRouter or Groq) and external scraping targets may restrict access based on geographic IP location. By default, the application attempts a direct connection. If you are operating in a restricted region, you can easily route Docker container traffic through your host machine's proxy client (e.g., NekoRay, Hiddify, or v2rayA).

---

### How It Works

Docker containers run inside an isolated virtual bridge network and cannot reach `127.0.0.1` on your host machine directly. To route traffic through a host-level proxy:

1. `extra_hosts` maps `host.docker.internal` to the host gateway (`172.17.0.1`).
2. Standard `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` environment variables instruct libraries like `httpx` and `huggingface_hub` to tunnel requests through the host proxy port.
3. `NO_PROXY` ensures internal service communication (`db`, `redis`, `searxng`) bypasses the proxy entirely.

---

### Setup Guide

Follow these steps if your AI requests or scraping tasks fail due to connection blocks or timeouts:

#### 1. Allow Inbound / LAN Connections in Your Proxy Client

By default, desktop proxy clients only listen on `127.0.0.1` (local loopback), which rejects Docker bridge traffic.

* **NekoRay:** Go to `Preferences` → `Basic Settings` → Check **"Allow LAN"** (or set Listen Address to `0.0.0.0`).
* **Hiddify:** Open Settings → Enable **"Allow Inbound Connections / Share over LAN"**.
* Note your local **HTTP proxy port** (commonly `2080`, `2081`, or `10809`).

#### 2. Allow the Proxy Port Through Your Firewall (Linux / Ubuntu)

If you are using `ufw`, open the proxy port so Docker bridge packets are not dropped:

```bash
sudo ufw allow 2080/tcp
sudo ufw reload
```

---

## Contributing

This project is a personal portfolio piece, but I warmly welcome bug reports, feature ideas, and pull requests. If you'd like to contribute:

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Ensure the tests pass (docker compose exec app pytest)
5. Open a pull request with a clear description
6. For larger changes, please open an issue first so we can discuss.

## License

[MIT](https://opensource.org/license/mit "click to see what is MIT license")

do whatever you want with the code, just keep the copyright notice.
