# API Endpoints: Frontend Contract

The Next.js frontend consumes **every endpoint** the existing HTMX UI uses, plus the three JSON highlight endpoints. This file is the authoritative contract — every row MUST be exercised by tests (spec §Frontend Contract Compatibility).

**Base URL**: `http://localhost:8000` (local dev)  
**Auth**: httpOnly `access_token` cookie (credentials: 'include' on all fetches)  
**CORS**: frontend origin `http://localhost:3000` added to `main.py` allowlist (sole backend edit)

---

## HTML/HTMX Endpoints (Root Path, `include_in_schema=False`)

These return HTML fragments or pages. The frontend **fetches them and parses the HTML** (or reconstructs the same data from JSON list endpoints where possible) — the contract is that these routes **continue to exist and behave identically** for the HTMX UI.

| # | Method | Path | Purpose | Used By (Screen/Action) | Auth | Success | Errors |
|---|--------|------|---------|------------------------|------|---------|--------|
| 1 | POST | `/logout` | Clear auth cookie, redirect to /login | Header logout button | None (cookie) | 303 → /login | — |
| 2 | POST | `/dashboard/projects` | Create project; returns fragment (HX-Request) or redirect | Dashboard create form | Cookie | 200 HTML fragment / 303 | 401 |
| 3 | GET | `/projects/{project_id}` | Full project detail page (HTML) | Direct page load (navigation) | Cookie | 200 HTML | 401, 403, 404 |
| 4 | GET | `/projects/{project_id}/notes/list` | Notes list fragment | Notes tab initial load, after create/edit | Cookie | 200 HTML | 401, 403 |
| 5 | GET | `/projects/{project_id}/notes/{note_id}/edit` | Inline edit form fragment | Note Edit button | Cookie | 200 HTML | 401, 403, 404 |
| 6 | PUT | `/projects/{project_id}/notes/{note_id}` | Update note; returns updated note item | Note edit form submit | Cookie | 200 HTML (note item) | 401, 403, 404, 422 |
| 7 | DELETE | `/projects/{project_id}/notes/{note_id}` | Delete note; returns empty | Note delete button | Cookie | 200 empty | 401, 403, 404 |
| 8 | GET | `/projects/{project_id}/notes/{note_id}/tags/available` | Available tags picker fragment | Attach tag picker open | Cookie | 200 HTML | 401, 403, 404 |
| 9 | POST | `/projects/{project_id}/notes/{note_id}/tags` | Attach tag (form: tag_id); returns note item | Tag picker selection | Cookie | 200 HTML (note item) | 401, 403, 404 |
| 10 | DELETE | `/projects/{project_id}/notes/{note_id}/tags/{tag_id}` | Detach tag; returns note item | Note tag badge × | Cookie | 200 HTML (note item) | 401, 403, 404 |
| 11 | GET | `/projects/{project_id}/links/list` | Links list fragment | Links tab initial load, after save | Cookie | 200 HTML | 401, 403 |
| 12 | GET | `/projects/{project_id}/links/{link_id}` | Single link fragment (poller) | Extraction status auto-refresh (3s) | Cookie | 200 HTML | 401, 403, 404 |
| 13 | GET | `/projects/{project_id}/links/{link_id}/content` | Extracted content fragment (inline view) | **Out of scope** (View/Hide toggle not ported) | Cookie | 200 HTML | 401, 403, 404 |
| 14 | POST | `/projects/{project_id}/links/{link_id}/extract` | Trigger re-extraction; returns link item | **Out of scope** (Re-extract button not ported) | Cookie | 200 HTML | 401, 403, 404 |
| 15 | DELETE | `/projects/{project_id}/links/{link_id}` | Delete link; returns empty | Link delete button | Cookie | 200 empty | 401, 403, 404 |
| 16 | POST | `/projects/{project_id}/search/web` | Web search; returns results fragment | Web Search tab submit | Cookie | 200 HTML | 401, 403 |
| 17 | POST | `/projects/{project_id}/links/save` | Save search result (form: url, title, snippet, search_query); returns saved confirmation | Search result "Save" button | Cookie | 200 HTML | 401, 403 |
| 18 | GET | `/projects/{project_id}/search/collected` | Full-text search results fragment (query: q) | Project search box (debounced) | Cookie | 200 HTML | 401, 403, 400 (empty q) |
| 19 | GET | `/projects/{project_id}/tags/list` | Tags list fragment | Tags tab initial load, after create/delete | Cookie | 200 HTML | 401, 403 |
| 20 | POST | `/projects/{project_id}/tags` | Create tag (form: name); returns tags list fragment | Tags create form | Cookie | 200 HTML | 401, 403, 409 (duplicate) |
| 21 | DELETE | `/projects/{project_id}/tags/{tag_id}` | Delete tag; returns empty | Tag delete button | Cookie | 200 empty | 401, 403, 404 |
| 22 | GET | `/projects/{project_id}/tags/{tag_id}/items` | Unified tag-filtered items fragment | Any tag badge click (notes, links, tags tab) | Cookie | 200 HTML | 401, 403, 404 |

**Frontend strategy for HTML fragments**: The frontend reconstructs the same data from the JSON list endpoints (e.g., `GET /api/v1/projects/{id}/notes` returns the notes with tags — no need to fetch `/notes/list` HTML). The HTML endpoints are **contractually supported** for the HTMX UI but the Next.js frontend uses the JSON equivalents where available. Exceptions:

- `POST /logout` — no JSON equivalent; must call directly (cookie clear + redirect).
- `GET /projects/{id}` — page navigation; Next.js replaces with client-side route (`/projects/[id]`).
- `POST /search/web`, `POST /links/save`, `GET /search/collected` — JSON equivalents exist under `/api/v1` (see below).

**Endpoints #13, #14 (View/Hide content, Re-extract)** — explicitly out of scope per clarification; the endpoints remain supported for HTMX UI but the Next.js port does not call them.

---

## JSON API Endpoints under `/api/v1` (Part of Frontend Contract)

### Documented in API-SPEC.md (existing, unchanged)

| # | Method | Path | Purpose | Used By | Auth | Success | Errors |
|---|--------|------|---------|---------|------|---------|--------|
| A1 | POST | `/api/v1/auth/register` | Register; sets cookie; returns user + token | Register form | None | 201 {id, email, created_at, access_token, token_type} | 409, 422, 429 |
| A2 | POST | `/api/v1/auth/login` | Login; sets cookie; returns token | Login form | None | 200 {access_token, token_type} | 401, 429 |
| A3 | GET | `/api/v1/projects` | List projects | Dashboard | Cookie | 200 ProjectRead[] | 401 |
| A4 | POST | `/api/v1/projects` | Create project (JSON) | **Alternative** to #2 (frontend uses JSON) | Cookie | 201 ProjectRead | 401, 422 |
| A5 | GET | `/api/v1/projects/{project_id}` | Get project | Workspace load | Cookie | 200 ProjectRead | 401, 403, 404 |
| A6 | GET | `/api/v1/projects/{project_id}/notes` | List notes (with tags, source_link_id) | Notes tab (replaces #4) | Cookie | 200 NoteRead[] | 401, 403 |
| A7 | POST | `/api/v1/projects/{project_id}/notes` | Create note (JSON: title, content, source_link_id) | Note create form | Cookie | 201 NoteRead | 401, 403, 422 |
| A8 | GET | `/api/v1/projects/{project_id}/notes/{note_id}` | Get single note | Inline edit prefill (replaces #5) | Cookie | 200 NoteRead | 401, 403, 404 |
| A9 | PUT | `/api/v1/projects/{project_id}/notes/{note_id}` | Update note (JSON) | Note edit save (replaces #6) | Cookie | 200 NoteRead | 401, 403, 404, 422 |
| A10 | DELETE | `/api/v1/projects/{project_id}/notes/{note_id}` | Delete note | Note delete (replaces #7) | Cookie | 204 | 401, 403, 404 |
| A11 | POST | `/api/v1/projects/{project_id}/notes/{note_id}/tags` | Attach tags (JSON: tag_ids[]) | Tag picker (replaces #9) | Cookie | 200 NoteRead | 401, 403, 404 |
| A12 | DELETE | `/api/v1/projects/{project_id}/notes/{note_id}/tags/{tag_id}` | Detach tag | Note tag badge × (replaces #10) | Cookie | 200 NoteRead | 401, 403, 404 |
| A13 | GET | `/api/v1/projects/{project_id}/links` | List links (with tags, extraction_status) | Links tab (replaces #11) | Cookie | 200 SavedLinkRead[] | 401, 403 |
| A14 | POST | `/api/v1/projects/{project_id}/links` | Save link (JSON: url, title, snippet, search_query) | Save button (replaces #17) | Cookie | 201 SavedLinkRead | 401, 403, 422 |
| A15 | GET | `/api/v1/projects/{project_id}/links/{link_id}` | Get single link | Extraction poller (replaces #12) | Cookie | 200 SavedLinkRead | 401, 403, 404 |
| A16 | DELETE | `/api/v1/projects/{project_id}/links/{link_id}` | Delete link | Link delete (replaces #15) | Cookie | 204 | 401, 403, 404 |
| A17 | POST | `/api/v1/projects/{project_id}/links/{link_id}/tags` | Attach tags to link | Link tag actions (if in scope) | Cookie | 200 SavedLinkRead | 401, 403, 404 |
| A18 | DELETE | `/api/v1/projects/{project_id}/links/{link_id}/tags/{tag_id}` | Detach tag from link | Link tag badge × | Cookie | 200 SavedLinkRead | 401, 403, 404 |
| A19 | POST | `/api/v1/projects/{project_id}/search` | Web search (JSON: query) | Web Search tab (replaces #16) | Cookie | 200 SearchResult[] | 401, 403, 502 (SearXNG down) |
| A20 | GET | `/api/v1/projects/{project_id}/search-collected?q=...` | Full-text search (JSON) | Project search (replaces #18) | Cookie | 200 CollectedSearchResult[] | 401, 403, 400 (empty q) |
| A21 | GET | `/api/v1/projects/{project_id}/tags` | List tags | Tags tab (replaces #19) | Cookie | 200 TagRead[] | 401, 403 |
| A22 | POST | `/api/v1/projects/{project_id}/tags` | Create tag (JSON) | Tags create (replaces #20) | Cookie | 201 TagRead | 401, 403, 409 |
| A23 | DELETE | `/api/v1/projects/{project_id}/tags/{tag_id}` | Delete tag | Tag delete (replaces #21) | Cookie | 204 | 401, 403, 404 |
| A24 | GET | `/api/v1/projects/{project_id}/export/markdown` | Download project as .md | Export button | Cookie or Bearer | 200 text/markdown | 401, 403, 404 |

### Undocumented in API-SPEC.md (Missing — part of frontend contract)

| # | Method | Path | Purpose | Used By | Auth | Success | Errors |
|---|--------|------|---------|---------|------|---------|--------|
| H1 | GET | `/api/v1/projects/{project_id}/links/{link_id}/highlights` | List highlights for a link | Reader load, after save/delete | Cookie | 200 HighlightRead[] | 401, 403, 404 |
| H2 | POST | `/api/v1/projects/{project_id}/links/{link_id}/highlights` | Create highlight (JSON: selected_text, annotation, start_offset, end_offset, color) | Highlight popup save | Cookie | 201 HighlightRead | 401, 403, 404, 422 |
| H3 | DELETE | `/api/v1/projects/{project_id}/links/{link_id}/highlights/{highlight_id}` | Delete highlight | Highlights panel Remove | Cookie | 204 | 401, 403, 404 |

**Note**: H1–H3 are implemented in `app/api/v1/links.py` with full auth/ownership but missing from API-SPEC.md. They **MUST** be documented when this feature's docs are updated (constitution Principle VIII).

---

## Frontend Fetch Strategy

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => ({})));
  if (res.status === 204) return undefined as T;
  return res.json();
}
```

**JSON endpoints used by frontend** (replaces HTML equivalents where possible): A1–A24, H1–H3.  
**HTML endpoints called directly**: `POST /logout` (cookie clear + redirect follow).  
**HTML endpoints preserved but not called by Next.js**: #3 (page), #4–#22 (data reconstructed from JSON A6, A13, A21, A20, etc.), #13–#14 (out of scope).

---

## Error Handling Contract

| Status | Frontend Behavior |
|--------|-------------------|
| 400 | Show specific message (e.g., "Search query required") |
| 401 | Redirect to `/login` with message "Session expired — please sign in again" (FR-029) |
| 403 | Show "You don't have access to this resource" (not-found view) |
| 404 | Show not-found view with navigation back |
| 409 | Show conflict message inline (duplicate tag, duplicate email) |
| 422 | Show validation errors from server (field-level) |
| 429 | Show "Rate limited — try again in X seconds" honoring `Retry-After` |
| 500 / network | Show "Something went wrong. Please try again." (FR-026) |

---

## Rate Limiting Awareness

- **Auth (register/login)**: IP-keyed, `AUTH_RATE_LIMIT_*` env vars. Exceeding → 429.
- **AI endpoints**: per-user budget, `AI_RATE_LIMIT_*`. Out of scope for port (no AI features ported).
- **Frontend**: no client-side rate limiting; debounce only (search 500ms).

---

## Endpoint Count Verification

- HTML/HTMX endpoints (spec table): **24** (rows 1–22 above, #3 counted, #13–14 flagged out-of-scope)
- JSON endpoints (documented): **24** (A1–A24)
- JSON endpoints (undocumented): **3** (H1–H3)
- **Total**: 51 rows; frontend actively calls ~30 (JSON + /logout), preserves contract for all 51.
