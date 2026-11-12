# UI Specification – Research Vault

> **Purpose**: This document describes every screen, component, and user interaction in the Research Vault UI. It is intended for a frontend developer who will work with (or rebuild) the user interface without modifying the existing backend API.

## 1. Overview

Research Vault is a self-hosted research and knowledge management tool. Users create projects, write notes, search the web via a self-hosted SearXNG instance or paste URLs directly, save links, extract full article content (saved as structured Markdown), highlight and annotate passages, and organise everything with tags. The UI communicates exclusively with the backend REST API (`/api/v1/…`) using **JWT authentication stored in a httpOnly `access_token` cookie** or the `Authorization: Bearer <token>` header.

The current reference UI is a **Next.js 14 (App Router), TypeScript, React, Tailwind CSS** application in `frontend/`, running on port 3000. API calls use relative URLs and are proxied to `http://localhost:8000` by the rewrites in `frontend/next.config.js` (`/api/:path*` → `http://localhost:8000/api/:path*`), keeping them same-origin with no CORS preflight.

The legacy server-rendered HTMX UI (Jinja2 + Pico.css) has been removed; only the JSON API remains as the backend surface.

---

## 2. Authentication & Session

- **Registration**: `POST /api/v1/auth/register` with `{email, password}`.
- **Login**: `POST /api/v1/auth/login` with `{email, password}`.
- **Logout**: `POST /api/v1/auth/logout` — clears the `access_token` cookie.
- Both register and login return `access_token` and set an **httpOnly cookie** named `access_token`.
- All subsequent requests include the `access_token` cookie (or the `Authorization: Bearer <token>` header). The frontend uses `credentials: 'include'` on direct backend calls.
- Protected pages (dashboard, project detail, reader) redirect to `/login` when the cookie is missing or invalid.

---

## 3. Page Inventory

### 3.1 Login Page (`/login`)

- **Fields**: email, password.
- **Submission**: POSTs to `/api/v1/auth/login` → sets cookie → redirects to `/dashboard`.
- **Links**: “Don’t have an account? Register” → `/register`.
- **Error handling**: Displays a message above the form if login fails.

### 3.2 Register Page (`/register`)

- **Fields**: email, password.
- **Submission**: POSTs to `/api/v1/auth/register` → sets cookie → redirects to `/dashboard`.
- **Links**: “Already have an account? Log in” → `/login`.

### 3.3 Dashboard (Projects List) – `/dashboard`

- **Header**: “Your projects”, user email, Logout button.
- **Project list**: Cards showing project name + description.
- **Create project**: Form with `name` (required) and `description` (optional). New project appears in the list immediately (optimistic update via React Query).
- **Navigation**: Click a project card → `/projects/{project_id}`.
- **Empty state**: “No projects yet. Create one above.”

### 3.4 Project Detail Page – `/projects/{project_id}`

This is the core workspace, split into **tabs**. Only one tab is visible at a time.

#### 3.4.1 Global elements (always visible)

- **Back link**: “← Back to projects” → `/dashboard`.
- **Search box**: Debounced full-text search across notes and links within this project. See §5.3.
- **Tag filter results area**: Displays notes and links matching the selected tag. See §5.2.
- **Export as Markdown button**: Downloads the whole project (notes, saved links, highlights) as a single `.md` file via `GET /api/v1/projects/{project_id}/export/markdown`.

#### 3.4.2 Tabs

Four tabs: **Notes**, **Links**, **Web Search**, **Tags**.

- **Tab switching**: Client-side via Next.js state. Default active tab: Notes.

---

**Notes Tab**

- **Create note form**: Title (required), Content (optional), Source link dropdown (optional — lists all saved links in this project).
- **Notes list**: Loaded from `GET /api/v1/projects/{project_id}/notes`. Each note shows title, content preview, attached tags (badges), Edit/Delete buttons.
- **Edit note**: Replace note with a pre-filled form; submit updates the note and refreshes the list.
- **Delete note**: Confirms then removes the note from the list.
- **Attach / detach tag**: Attach via `POST /api/v1/projects/{project_id}/notes/{note_id}/tags`; detach via `DELETE .../tags/{tag_id}`.

---

**Links Tab**

- **Links list**: Loaded from `GET /api/v1/projects/{project_id}/links`. Each link shows title, URL (truncated), extraction status badge (“Pending” / “Completed” / “Failed”), tags (badges), title link → reader page, Delete button.
- **Reading-list status**: Each link can be set to `to_read`, `reading`, `done`, or `archived` via `PATCH /api/v1/projects/{project_id}/links/{link_id}/status`; filtering by status is supported via `?status=...`.
- **Re-extract**: Manual “Re-extract” button triggers `POST /api/v1/projects/{project_id}/link/{link_id}/re-extract`.
- **No links state**: “No links saved yet.”

---

**Web Search Tab**

- **Search form**: Text input + Search button. Results from `POST /api/v1/projects/{project_id}/search`.
- **Manual extract form**: Paste any URL directly → `POST /api/v1/projects/{project_id}/links/manual-extract` (bypasses SearXNG).
- **Results**: Title (opens URL in new tab), snippet, engine badge, Save button → `POST /api/v1/projects/{project_id}/links` with `url`, `title`, `snippet`, `search_query`.

---

**Tags Tab**

- **Create tag form**: Tag name input (unique per project).
- **Tags list**: Loaded from `GET /api/v1/projects/{project_id}/tags`. Each tag shows name + Delete button.
- **Tag filtering**: Clicking a tag name triggers `GET /api/v1/projects/{project_id}/tags/{tag_id}/items` and shows the unified list of tagged notes & links.

#### 3.4.3 Notes & Links interactions

- **Attach tag**: `POST .../notes/{note_id}/tags` or `POST .../links/{link_id}/tags` with `{"tag_ids": [...]}`.
- **Detach tag**: `DELETE .../notes/{note_id}/tags/{tag_id}` or `DELETE .../links/{link_id}/tags/{tag_id}`.

---

### 3.5 Reader Mode Page – `/projects/{project_id}/links/{link_id}/read`

This page shows the full extracted article text and supports highlighting.

- **Back link**: “← Back to [project name]” → `/projects/{project_id}`.
- **“+ Add note about this”**: Returns to project page with `?source_link_id={link_id}` and the Notes tab active.
- **Article title & source URL** (opens in new tab).
- **Article content**: Rendered as structured Markdown via `react-markdown` (headings, paragraphs, lists, code blocks). If extraction status is not “completed”, shows “Content not yet extracted.”

#### 3.5.1 Highlight System

- **Selection**: User selects text inside the article.
- **Popup**: Small form near the selection with:
  - `selected_text`, `start_offset`, `end_offset` (computed against the rendered text stream).
  - Annotation input (optional).
  - Colour picker: yellow, blue, green, orange, purple, grey.
  - Save / Close buttons.
- **Submission**: `POST /api/v1/projects/{project_id}/links/{link_id}/highlights` (JSON body). Response updates the highlights list and re-applies visual `<mark>` marks.
- **Highlights panel**: Lists all highlights for the link with quoted text, annotation, colour swatch, and Remove button → `DELETE .../highlights/{highlight_id}`.
- **Persistent marks**: Highlights are painted as `<mark>` elements on page load and after any change, using `start_offset`/`end_offset`.

#### 3.5.2 AI Features in Reader

- **“Explain this”**: Select a passage → AI explanation saved as a highlight annotation (`POST .../links/{link_id}/explain`).
- **Summarise**: Generate an AI summary stored on the link (`POST .../links/{link_id}/summarise`).
- **Semantic rerank**: In search results, a “Rerank” button triggers `POST .../search-semantic` to reorder results by semantic relevance.

---

## 4. User Flows

### 4.1 Registration & Login

1. Visit `/` → redirect to `/login`.
2. Click “Register” → fill form → redirect to `/dashboard`.
3. Login → fill credentials → redirect to `/dashboard`.

### 4.2 Creating a Project

1. On dashboard, fill in project name → press Enter / click “Create”.
2. New project card appears. Click it → `/projects/{id}`.

### 4.3 Researching a Topic

1. In project, go to **Web Search** tab, type query, search.
2. Browse results, click “Save” on interesting links (or paste a URL directly via Manual Extract).
3. Switch to **Links** tab – see saved links with extraction status.
4. When status becomes “Completed”, click title → Reader page.
5. Read the article, highlight important passages (pick colour), add annotations.
6. Click “+ Add note about this” → return to project with source pre-selected.
7. Write a note synthesising the information. It automatically links back to the source.
8. Add tags to both notes and links for organisation.

### 4.4 Searching and Filtering

1. Use the project search box to find terms across notes and links.
2. Click any tag badge to filter all items with that tag.
3. Filter links by reading-list status (`to_read` / `reading` / `done` / `archived`).

---

## 5. Global Interactions

### 5.1 Tag Filtering

- Clicking any tag (in notes list, links list, tags tab) sends `GET /api/v1/projects/{project_id}/tags/{tag_id}/items`.
- Results are displayed in a dedicated area (`#tag-filter-results`). The area can be cleared with a “Clear filter” button.
- No page reload: the tabs remain intact.

### 5.2 Full-Text Search (Collected)

- Input in the project page triggers a debounced search (500ms after typing) or on form submit.
- `GET /api/v1/projects/{project_id}/search-collected?q=...` returns a unified list of matching notes and links, ordered by relevance. Each result shows type, title, snippet, and a link.
- Results replace the content of `#collected-search-results` (below the search box).

---

## 6. API Interactions Summary

The Next.js frontend calls the JSON API under `/api/v1` (proxied by `next.config.js`). All routes require authentication and enforce project ownership:

| UI action | Endpoint |
|-----------|----------|
| Register | `POST /api/v1/auth/register` |
| Login | `POST /api/v1/auth/login` |
| Logout | `POST /api/v1/auth/logout` |
| List / create projects | `GET|POST /api/v1/projects` |
| Get / update / delete project | `GET|PUT|DELETE /api/v1/projects/{id}` |
| Notes CRUD | `GET|POST /api/v1/projects/{id}/notes`, `GET|PUT|DELETE /api/v1/projects/{id}/notes/{note_id}` |
| Notes tags | `POST|DELETE /api/v1/projects/{id}/notes/{note_id}/tags[/{tag_id}]` |
| Links CRUD | `GET|POST /api/v1/projects/{id}/links`, `GET|DELETE /api/v1/projects/{id}/links/{link_id}` |
| Link status | `PATCH /api/v1/projects/{id}/links/{link_id}/status` |
| Link re-extract | `POST /api/v1/projects/{id}/link/{link_id}/re-extract` |
| Link tags | `POST|DELETE /api/v1/projects/{id}/links/{link_id}/tags[/{tag_id}]` |
| Highlights | `GET|POST /api/v1/projects/{id}/links/{link_id}/highlights`, `DELETE .../highlights/{highlight_id}` |
| Explain | `POST /api/v1/projects/{id}/links/{link_id}/explain` |
| Summarise | `POST /api/v1/projects/{id}/links/{link_id}/summarise` |
| Web search | `POST /api/v1/projects/{id}/search` |
| Manual extract | `POST /api/v1/projects/{id}/links/manual-extract` |
| Full-text search | `GET /api/v1/projects/{id}/search-collected?q=...` |
| Semantic search | `POST /api/v1/projects/{id}/search-semantic` |
| Tags | `GET|POST|DELETE /api/v1/projects/{id}/tags`, `GET .../tags/{tag_id}/items` |
| Tag suggestions | `POST /api/v1/projects/{id}/suggest-tags` |
| Bulk tags | `POST /api/v1/projects/{id}/bulk-tags` |
| Markdown export | `GET /api/v1/projects/{id}/export/markdown` |
| Roadmap | `POST /api/v1/roadmap` |

All these routes are protected and require a valid session (cookie or Bearer token). They also enforce project ownership (only the owner of the project can access its data).

See `API-SPEC.md` for full request/response details.