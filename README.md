![Stars](https://img.shields.io/github/stars/AminodinAkbari/Research-vault)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

# Research Vault

A self-hosted research and knowledge management platform you can run on your own machine. No AI, no cloud dependencies, no subscriptions. Just you, your ideas, and a clean API to organize them.

> ⚠️ **Active development** – new features land every few days. Check back often or star the repo to follow along.

---

⭐ If you find this useful, please consider starring the repo!

## What is this?

Research Vault helps you collect, organize, and rediscover information from the web and your own notes. Think of it as a personal knowledge base for solo researchers, tinkerers, and lifelong learners.

**It is NOT**

- an AI chatbot or LLM wrapper
- a SaaS product
- a complex multi‑user collaboration tool

**It IS**

- a focused, offline‑capable research tool you host yourself
- a showcase of modern backend engineering (FastAPI, async Python, clean architecture)
- completely free and open source

---

## Features (so far)

All of the following are implemented and tested:

- **User authentication** – register, login, JWT-protected endpoints
- **Research projects** – create isolated containers for different topics
- **Notes** – write plain‑text notes inside any project (full CRUD)
- **Tags** – organize notes with per‑project tags (attach/detach, list)
- **User isolation** – every request is scoped to the logged‑in user
- **Full test suite** – async integration tests for all endpoints
- **Docker Compose** – one command to start the whole stack

## Coming soon

These features are planned or under active consideration.
They’re all designed to make research flow smoother without turning the app into something it’s not.

### Upcoming features

- **Research Kickstart** – type a topic you want to learn and get an AI‑generated roadmap with suggested search keywords, so you never start your research from scratch.
- **Markdown export (whole project)** – compile a project’s notes, saved links, highlights, and annotations into a single Markdown file. Great for archiving, sharing, or importing into other tools.
- **Bulk tag operations** – select multiple notes and links to apply or remove tags in one go. Organise faster.
- **Reading‑list statuses** – built‑in workflow states for links (e.g., “to‑read”, “reading”, “done”, “archived”). More than just tags – these can drive filtered views and reminders.
- **Full‑text PDF / EPUB extraction** – expand the background extraction pipeline to handle PDFs and EPUBs, not just web pages. Your reading stays inside the vault.
- **Progressive Web App (PWA)** – work offline on your mobile device and sync automatically when you’re back online. Read and annotate anywhere.

### AI‑powered features (under consideration)

All AI features are designed as **one‑shot helpers**, not chatbots. They’re there when you need them, invisible when you don’t.

- 
- **Tag suggestion** – when you save a link or write a note, the system can suggest relevant tags based on your existing vocabulary. You always approve or reject them.
- **Smart summarisation** – a “Summarise this article” button that generates a short summary from the extracted content and saves it as a note, linked to the source.
- **Semantic search** – optional upgrade to full‑text search that understands meaning, not just keywords. Still search, not conversation.
- **“Explain this” highlight** – in the reader, select a passage and click “Explain this” to get a concise explanation saved as an annotation.

---

## Tech Stack

| Layer            | Technology                                                        |
| ---------------- | ----------------------------------------------------------------- |
| API framework    | FastAPI (async)                                                   |
| Database         | PostgreSQL 16 + SQLAlchemy 2.0 (async)                            |
| Migrations       | Alembic                                                           |
| Validation       | Pydantic v2                                                       |
| Caching / broker | Redis                                                             |
| Background tasks | Celery (using Redis as broker)                                    |
| Search engine    | SearXNG (self‑hosted)                                            |
| Containerization | Docker Compose                                                    |
| Auth             | JWT via`python-jose`, password hashing with `passlib[bcrypt]` |

---

## Getting Started

You need Docker and Docker Compose installed. That's it.

### 1. Clone the repo

```bash
git clone https://github.com/aminodinakbari/research-vault.git
cd research-vault
```

## 2. Set up environment

```bash
cp .env.example .env
```

## 3. Start everything

```bash
docker compose up -d
```

This launches:

- The FastAPI app (on http://localhost:8000)
- PostgreSQL
- Redis
- SearXNG (for future search features)
- A Celery worker (for background tasks)

## 4. Run database migrations

```bash
docker compose exec app alembic upgrade head
```

## 5. Open the interactive API docs

Go to [http://localhost:8000/docs].
You can register a user, create projects, write notes, and explore every endpoint directly from the browser.

---

## Usage (via Swagger)

Once the app is running:

- Use POST /api/v1/auth/register to create an account.
- Use POST /api/v1/auth/login to get a JWT token, then click Authorize in Swagger and paste it.
- Create a project with POST /api/v1/projects.
- Inside that project, create notes with POST /api/v1/projects/{id}/notes.
- Manage tags with the /tags endpoints, and attach them to notes.

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
