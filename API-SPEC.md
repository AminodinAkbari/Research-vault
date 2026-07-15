# Research Vault API Specification

**Base URL:** `/api/v1`
**Authentication:** JWT Bearer token (Authorization header) **or** httpOnly cookie (`access_token`)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Projects](#projects)
3. [Notes](#notes)
4. [Links](#links)
5. [Tags](#tags)
6. [Highlights (UI endpoints)](#highlights-ui-endpoints)
7. [Search](#search)
8. [Error Codes](#error-codes)

---

## Authentication

All endpoints under `/api/v1/projects/**`, `/api/v1/notes/**`, `/api/v1/tags/**`, `/api/v1/links/**`, and `/api/v1/search-collected` require authentication.

**Methods:**

- **JWT Bearer:** `Authorization: Bearer <token>`
- **Cookie:** `access_token=<token>` (httpOnly, SameSite=lax)

### POST /api/v1/auth/register

Register a new user account.

**Authentication:** None

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error Codes:**

- `409 Conflict` — Email already registered

---

### POST /api/v1/auth/login

Authenticate and receive JWT token.

**Authentication:** None

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Response Headers:**

- `Set-Cookie: access_token=eyJ...; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400`

**Error Codes:**

- `401 Unauthorized` — Invalid credentials (`WWW-Authenticate: Bearer` header included)

---

## Projects

All project endpoints require authentication (JWT or cookie).
**Base path:** `/api/v1/projects`

### POST /api/v1/projects

Create a new project owned by the current user.

**Request Body:**

```json
{
  "name": "AI Research",
  "description": "Collecting papers on LLMs"
}
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "AI Research",
  "description": "Collecting papers on LLMs",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Codes:**

- `401 Unauthorized` — Not authenticated

---

### GET /api/v1/projects

List all projects owned by the current user.

**Response (200 OK):**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "AI Research",
    "description": "Collecting papers on LLMs",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### GET /api/v1/projects/

Get a single project by ID. Requires ownership.

**Path Parameters:**

- `project_id` (UUID) — Project UUID

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "AI Research",
  "description": "Collecting papers on LLMs",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Codes:**

- `401 Unauthorized` — Not authenticated
- `403 Forbidden` — Not project owner
- `404 Not Found` — Project not found

---

### PUT /api/v1/projects/

Partially update a project.

**Path Parameters:**

- `project_id` (UUID) — Project UUID

**Request Body (all fields optional):**

```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Updated Name",
  "description": "Updated description",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Codes:**

- `401 Unauthorized` — Not authenticated
- `403 Forbidden` — Not project owner
- `404 Not Found` — Project not found

---

### DELETE /api/v1/projects/

Delete a project and all its notes, links, tags, and highlights.

**Path Parameters:**

- `project_id` (UUID) — Project UUID

**Response (204 No Content)**

**Error Codes:**

- `401 Unauthorized` — Not authenticated
- `403 Forbidden` — Not project owner
- `404 Not Found` — Project not found

---

## Notes

All note endpoints are scoped to a project.
**Base path:** `/api/v1/projects/{project_id}/notes`
Authentication required (project ownership enforced).

### POST /api/v1/projects//notes

Create a new note in the project.

**Path Parameters:**

- `project_id` (UUID)

**Request Body:**

```json
{
  "title": "Paper Notes: Attention Is All You Need",
  "content": "Key insight: self-attention mechanism...",
  "tag_ids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
  "source_link_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
}
```

**Field Notes:**

- `tag_ids` — Optional array of existing tag UUIDs to attach
- `source_link_id` — Optional UUID of a saved link this note originates from

**Response (201 Created):**

```json
{
  "id": "cccccccc-dddd-eeee-ffff-000000000001",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Paper Notes: Attention Is All You Need",
  "content": "Key insight: self-attention mechanism...",
  "source_link_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "tags": [
    { "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "transformer" }
  ]
}
```

**Error Codes:**

- `401 Unauthorized`
- `403 Forbidden` — Not project owner
- `404 Not Found` — Project or source_link not found

---

### GET /api/v1/projects//notes

List all notes in the project.

**Response (200 OK):**

```json
[
  {
    "id": "cccccccc-dddd-eeee-ffff-000000000001",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Paper Notes: Attention Is All You Need",
    "content": "Key insight: self-attention mechanism...",
    "source_link_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    "created_at": "2024-01-15T11:00:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "tags": [
      { "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "transformer" }
    ]
  }
]
```

---

### GET /api/v1/projects//notes/

Get a single note by ID.

**Path Parameters:**

- `project_id` (UUID)
- `note_id` (UUID)

**Response (200 OK):**

```json
{
  "id": "cccccccc-dddd-eeee-ffff-000000000001",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Paper Notes: Attention Is All You Need",
  "content": "Key insight: self-attention mechanism...",
  "source_link_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "tags": [
    { "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "transformer" }
  ]
}
```

**Error Codes:**

- `404 Not Found` — Note not found in this project

---

### PUT /api/v1/projects//notes/

Partially update a note.

**Request Body (all fields optional):**

```json
{
  "title": "Updated Title",
  "content": "Updated content",
  "tag_ids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
  "source_link_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
}
```

**Response (200 OK):** Updated `NoteRead` object (same as GET)

**Error Codes:**

- `404 Not Found` — Note not found

---

### DELETE /api/v1/projects//notes/

Delete a note.

**Response (204 No Content)**

**Error Codes:**

- `404 Not Found` — Note not found

---

### POST /api/v1/projects//notes//tags

Attach one or more tags to a note.

**Request Body:**

```json
{
  "tag_ids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"]
}
```

**Response (200 OK):** Updated `NoteRead` object

**Error Codes:**

- `404 Not Found` — Note not found

---

### DELETE /api/v1/projects//notes//tags/

Detach a tag from a note.

**Path Parameters:**

- `note_id` (UUID)
- `tag_id` (UUID)

**Response (200 OK):** Updated `NoteRead` object

**Error Codes:**

- `404 Not Found` — Note not found

---

## Links

All link endpoints are scoped to a project.
**Base path:** `/api/v1/projects/{project_id}`
Authentication required (project ownership enforced).

### POST /api/v1/projects//search

Run an external web search via SearXNG.

**Request Body:**

```json
{
  "query": "transformer architecture attention mechanism"
}
```

**Response (200 OK):**

```json
[
  {
    "title": "Attention Is All You Need",
    "url": "https://arxiv.org/abs/1706.03762",
    "snippet": "The dominant sequence transduction models...",
    "engine": "arxiv"
  }
]
```

**Special Behaviour:**

- Calls external SearXNG instance (configured via `SEARXNG_URL` env var)
- No project data is written; results are returned for user to save as links

**Error Codes:**

- `502 Bad Gateway` — SearXNG unreachable
- `504 Gateway Timeout` — SearXNG timeout

---

### POST /api/v1/projects//links

Save a new link to the project. Triggers async content extraction.

**Request Body:**

```json
{
  "url": "https://arxiv.org/abs/1706.03762",
  "title": "Attention Is All You Need",
  "snippet": "The dominant sequence transduction models...",
  "search_query": "transformer architecture",
  "tag_ids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
}
```

**Field Notes:**

- `url` — Required, must be valid HTTP(S) URL
- `title` — Required, max 500 chars
- `snippet` — Optional preview text
- `search_query` — Optional query that produced this result
- `tag_ids` — Optional existing tag UUIDs to attach immediately

**Response (201 Created):**

```json
{
  "id": "dddddddd-eeee-ffff-0000-111111111111",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://arxiv.org/abs/1706.03762",
  "title": "Attention Is All You Need",
  "snippet": "The dominant sequence transduction models...",
  "search_query": "transformer architecture",
  "extracted_content": null,
  "extraction_status": "pending",
  "created_at": "2024-01-15T11:30:00Z",
  "tags": [
    { "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "transformer" }
  ]
}
```

**Special Behaviour:**

- Link creation triggers **async content extraction** (background task)
- `extraction_status` will be `pending` → `completed` | `failed`
- Extracted content stored in `extracted_content` field
- Client should poll or use WebSocket (UI) for completion

**Error Codes:**

- `401 Unauthorized`
- `403 Forbidden` — Not project owner
- `404 Not Found` — Tag(s) not found in project

---

### GET /api/v1/projects//links

List all saved links in the project.

**Response (200 OK):**

```json
[
  {
    "id": "dddddddd-eeee-ffff-0000-111111111111",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://arxiv.org/abs/1706.03762",
    "title": "Attention Is All You Need",
    "snippet": "The dominant sequence transduction models...",
    "search_query": "transformer architecture",
    "extracted_content": "Full extracted text...",
    "extraction_status": "completed",
    "created_at": "2024-01-15T11:30:00Z",
    "tags": [
      { "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "transformer" }
    ]
  }
]
```

---

### GET /api/v1/projects//links/

Get a single saved link by ID.

**Response (200 OK):** Single `SavedLinkRead` object (same structure as list item)

**Error Codes:**

- `404 Not Found` — Link not found in this project

---

### DELETE /api/v1/projects//links/

Delete a saved link and its highlights.

**Response (204 No Content)**

**Error Codes:**

- `404 Not Found` — Link not found

---

### POST /api/v1/projects//links//tags

Attach tags to a saved link.

**Request Body:**

```json
{
  "tag_ids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
}
```

**Response (200 OK):** Updated `SavedLinkRead` object

**Error Codes:**

- `404 Not Found` — Link not found

---

### DELETE /api/v1/projects//links//tags/

Detach a tag from a saved link.

**Response (200 OK):** Updated `SavedLinkRead` object

**Error Codes:**

- `404 Not Found` — Link not found

---

## Tags

All tag endpoints are scoped to a project.
**Base path:** `/api/v1/projects/{project_id}/tags`
Authentication required (project ownership enforced).

### POST /api/v1/projects//tags

Create a new tag in the project.

**Request Body:**

```json
{
  "name": "transformer"
}
```

**Response (201 Created):**

```json
{
  "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "transformer",
  "created_at": "2024-01-15T10:35:00Z"
}
```

**Error Codes:**

- `409 Conflict` — Tag with this name already exists in project
- `404 Not Found` — Project not found

---

### GET /api/v1/projects//tags

List all tags in the project.

**Response (200 OK):**

```json
[
  {
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "transformer",
    "created_at": "2024-01-15T10:35:00Z"
  }
]
```

---

### DELETE /api/v1/projects//tags/

Delete a tag by ID. Removes tag from all notes/links.

**Path Parameters:**

- `tag_id` (UUID)

**Response (204 No Content)**

**Error Codes:**

- `404 Not Found` — Tag not found in this project

---

## Highlights (UI Endpoints)

Highlight endpoints are **server-rendered HTML** (HTMX) endpoints, mounted at root path (`/projects/...`), not under `/api/v1`.
Authentication via cookie only.

**Base path:** `/projects/{project_id}/links/{link_id}/highlights`

### GET /projects//links//read

Reader mode page displaying link content with highlights.

**Response:** HTML (`text/html`)

---

### POST /projects//links//highlights

Create a highlight on a saved link's extracted content.

**Form Data:**

- `selected_text` (string, required) — Exact text selected by user
- `annotation` (string, optional) — Free-text note
- `start_offset` (int, default 0) — Character offset in `extracted_content`
- `end_offset` (int, default 0) — End character offset
- `color` (string, optional) — Highlight color (e.g., `#ffeb3b`)

**Special Behaviour:**

- Offsets are **not validated** against source text server-side (MVP)
- Highlight stored with exact `selected_text`; `start_offset`/`end_offset` are metadata for client positioning

**Response:** HTML fragment (`_highlights_list.html` partial)

**Error Codes:**

- `404 Not Found` — Link not found

---

### DELETE /projects//links//highlights/

Delete a highlight.

**Response (200 OK):** Empty body

**Error Codes:**

- `404 Not Found` — Link or highlight not found

---

## Search

### GET /api/v1/projects//search-collected

Full-text search across notes and saved links in the current project using PostgreSQL FTS (tsvector/tsquery).

**Query Parameters:**

- `q` (string, required, min 1 char) — Search query (plainto_tsquery syntax)

**Response (200 OK):**

```json
[
  {
    "type": "note",
    "id": "cccccccc-dddd-eeee-ffff-000000000001",
    "title": "Paper Notes: Attention Is All You Need",
    "snippet": "Key insight: self-attention mechanism...",
    "rank": 0.85
  },
  {
    "type": "link",
    "id": "dddddddd-eeee-ffff-0000-111111111111",
    "title": "Attention Is All You Need",
    "snippet": "The dominant sequence transduction models...",
    "rank": 0.72
  }
]
```

**Special Behaviour:**

- Uses PostgreSQL `tsvector`/`tsquery` with `websearch_to_tsquery` for ranking
- Searches `notes.title`, `notes.content`, `saved_links.title`, `saved_links.extracted_content`
- Results ordered by relevance rank descending
- `snippet` is a headline excerpt (ts_headline)

**Error Codes:**

- `400 Bad Request` — Query parameter `q` missing or empty
- `401 Unauthorized`
- `403 Forbidden` — Not project owner

---

## Error Codes Summary

| Code    | Meaning                                                  |
| ------- | -------------------------------------------------------- |
| `400` | Bad Request — Validation error (missing/invalid params) |
| `401` | Unauthorized — Missing or invalid JWT/cookie            |
| `403` | Forbidden — Authenticated but not resource owner        |
| `404` | Not Found — Resource doesn't exist in scope             |
| `409` | Conflict — Duplicate resource (email, tag name)         |
| `422` | Unprocessable Entity — Pydantic validation error        |
| `502` | Bad Gateway — External service (SearXNG) failed         |
| `504` | Gateway Timeout — External service timeout              |

---

## Data Models Reference

### UserRead

```json
{
  "id": "uuid",
  "email": "string",
  "created_at": "datetime"
}
```

### ProjectRead

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "string",
  "description": "string|null",
  "created_at": "datetime"
}
```

### NoteRead

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "title": "string",
  "content": "string",
  "source_link_id": "uuid|null",
  "created_at": "datetime",
  "updated_at": "datetime",
  "tags": [TagResponse]
}
```

### SavedLinkRead

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "url": "string",
  "title": "string",
  "snippet": "string",
  "search_query": "string|null",
  "extracted_content": "string|null",
  "extraction_status": "pending|completed|failed",
  "created_at": "datetime",
  "tags": [TagResponse]
}
```

### TagRead

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "string",
  "created_at": "datetime"
}
```

### TagResponse (embedded)

```json
{
  "id": "uuid",
  "name": "string"
}
```

### CollectedSearchResult

```json
{
  "type": "note|link",
  "id": "string",
  "title": "string",
  "snippet": "string",
  "rank": "float"
}
```

### SearchResult (SearXNG)

```json
{
  "title": "string",
  "url": "string",
  "snippet": "string",
  "engine": "string"
}
```

---

## Authentication Flow Summary

1. **Register** → `POST /api/v1/auth/register` → Returns `access_token` + sets httpOnly cookie
2. **Login** → `POST /api/v1/auth/login` → Returns `access_token` + sets httpOnly cookie
3. **Authenticated requests** → Include either:
   - Header: `Authorization: Bearer <access_token>`
   - Cookie: `access_token=<access_token>` (automatic with browser)
4. **Project-scoped endpoints** → Require ownership validated via `get_current_project` dependency
