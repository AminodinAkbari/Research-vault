
# UI Specification – Research Vault

> **Purpose**: This document describes every screen, component, and user interaction in the current Research Vault UI. It is intended for a frontend developer who will rebuild the user interface (with React, Vue, Svelte, or improved HTML) without modifying the existing backend API.

---

## 1. Overview

Research Vault is a self‑hosted research and knowledge management tool. Users create projects, write notes, search the web via a self‑hosted SearXNG instance, save links, extract full article content, highlight and annotate passages, and organise everything with tags. The UI communicates exclusively with the backend REST API (`/api/v1/…`) using **JWT authentication stored in a cookie**.

The current reference UI uses **Jinja2 templates + HTMX + Pico.css**. The new UI can use any frontend framework; the behaviour described here is the target specification.

---

## 2. Authentication & Session

- **Registration**: `POST /api/v1/auth/register` with `{email, password}`.
- **Login**: `POST /api/v1/auth/login` with `{email, password}`.
- Both endpoints return a JSON response containing `access_token` and set an **httpOnly cookie** named `access_token`.
- All subsequent requests to the API (or UI routes) must include this cookie (or the `Authorization: Bearer <token>` header). The UI routes use the cookie automatically.
- **Logout**: `POST /logout` clears the cookie and redirects to `/login`.

Protected pages (dashboard, project detail, reader) check the cookie. If the cookie is missing or invalid, the user is redirected to `/login` (HTTP 303).

---

## 3. Page Inventory

### 3.1 Login Page (`/login`)

- **Fields**: email, password.
- **Form submission**: POSTs to `/api/v1/auth/login` (or the UI route that does the same) → sets the cookie and redirects to `/dashboard`.
- **Links**: “Don’t have an account? Register” → `/register`.
- **Error handling**: Display a message above the form if login fails (e.g., wrong credentials).
- **Responsiveness**: centred card, mobile‑friendly.

### 3.2 Register Page (`/register`)

- **Fields**: email, password.
- **Form submission**: POSTs to `/api/v1/auth/register` → automatically logs in (sets cookie) → redirects to `/dashboard`.
- **Links**: “Already have an account? Log in” → `/login`.
- **Validation**: email format, password minimum length (client‑side, backend also validates).

### 3.3 Dashboard (Projects List) – `/dashboard`

- **Header**: “Your projects”, user email, Logout button.
- **Project list**: Cards (or list items) showing project name + description.
- **Create project**: Inline form with `name` (required) and `description` (optional). Submitting via HTMX appends the new project to the list without a page reload. Falls back to full page reload if JavaScript is disabled.
- **Navigation**: Click a project card → `/projects/{project_id}`.
- **Empty state**: “No projects yet. Create one above.”

### 3.4 Project Detail Page – `/projects/{project_id}`

This is the core workspace, split into **tabs**. Only one tab is visible at a time.

#### 3.4.1 Global elements (always visible)

- **Back link**: “← Back to projects” → `/dashboard`.
- **Search box**: Live full‑text search across notes and links within this project. See §5.3.
- **Tag filter results area**: Where tag‑filtered items appear. See §5.2.

#### 3.4.2 Tabs

Four tabs: **Notes**, **Links**, **Web Search**, **Tags**.

- **Tab switching**: Client‑side only. Clicking a tab hides all panels and shows the clicked tab’s panel. Default active tab: Notes. If the page is loaded with a URL hash `#notes-panel` (e.g., from the reader’s “Add note about this” link), the Notes tab is activated automatically.

---

**Notes Tab**

- **Create note form**: Title (required), Content (optional), **Source link** dropdown (optional). The dropdown lists all saved links in this project. If the page was loaded with `?source_link_id=...`, that link is pre‑selected.
- **Notes list**: Loads asynchronously via `GET /projects/{project_id}/notes/list` (returns HTML fragment). Each note shows:
  - Title
  - Content preview
  - Source link (clickable → opens the reader for that link)
  - Attached tags (badges)
  - Edit / Delete buttons
- **Edit note**: Inline. Clicking “Edit” replaces the note with a form pre‑filled with the current data. Submit updates the note and refreshes the list.
- **Delete note**: Prompts confirmation. On success, the note is removed from the DOM.
- **Attach tag**: Each note has a “+” button that shows a small dropdown (or inline list) of available tags. Selecting a tag attaches it and updates the note’s tag list.
- **Detach tag**: Clicking a tag badge detaches it.

---

**Links Tab**

- **Links list**: Loads asynchronously via `GET /projects/{project_id}/links/list`. Each link shows:
  - Title (clickable → opens reader page)
  - URL (truncated)
  - Extraction status badge: “Pending”, “Completed”, “Failed”
  - Tags (badges)
  - “Show content” / “View” button → opens reader page for that link
  - Delete button
- **No links state**: “No links saved yet.”

---

**Web Search Tab**

- **Search form**: Text input + “Search” button.
- **Results area**: Loaded via HTMX after `POST /projects/{project_id}/search/web` (or GET if you prefer). Each result shows:
  - Title (clickable → opens URL in a new tab)
  - Snippet
  - Search engine name
  - **“Save” button**: Saves the result as a link in this project. The form sends `url`, `title`, `snippet`, `search_query` (the original search term). On success, the result can show a “Saved!” confirmation, or the link list is refreshed.
- **No results**: “No results found.” or “SearXNG is unavailable.” on error.

---

**Tags Tab**

- **Create tag form**: Input for tag name (unique per project). Submitting appends the tag to the list.
- **Tags list**: Loads asynchronously. Each tag shows:
  - Name
  - Delete button
- **Tag filtering**: Clicking a tag name anywhere in the project (notes list, links list, tags tab) triggers `GET /projects/{project_id}/tags/{tag_id}/items` and displays the unified list of notes & links tagged with it in the `#tag-filter-results` area (above the tabs). See §5.2.

#### 3.4.3 Notes & Links list interactions

- **Attach tag** (notes/links): Opens a small dropdown populated via `GET /projects/{project_id}/tags/list` (or pre‑fetched). Selecting a tag sends `POST /projects/{project_id}/notes/{note_id}/tags` (or `/links/{link_id}/tags`) with `{"tag_ids": [...]}`. The item’s tag list updates immediately.
- **Detach tag**: `DELETE /projects/{project_id}/notes/{note_id}/tags/{tag_id}`.

---

### 3.5 Reader Mode Page – `/projects/{project_id}/links/{link_id}/read`

This page shows the full extracted article text and supports highlighting.

- **Back link**: “← Back to [project name]” → `/projects/{project_id}`.
- **“+ Add note about this” button**: Takes the user back to the project page with `?source_link_id={link_id}#notes-panel`. The Notes tab opens and the source link dropdown is pre‑selected.
- **Article title** & **source URL** (opens in new tab).
- **Article content**: Displayed as plain text inside `#reader-article`. The `extracted_content` is rendered with `|safe` (no HTML escaping, but it’s just plain text). If extraction status is not “completed”, show “Content not yet extracted.” instead.

#### 3.5.1 Highlight System

- **Selection**: User selects any text inside the article.
- **Popup**: A small form appears near the selection with:
  - Hidden fields: `selected_text`, `start_offset`, `end_offset` (computed relative to the whole article text).
  - Annotation input (optional).
  - **Colour picker**: 6 small circles (yellow, blue, green, orange, purple, grey). Clicking a circle sets the colour and submits the form.
  - “Save” button (submits without a specific colour – defaults to yellow).
  - “✕” button to close the popup.
- **Submission**: `POST /projects/{project_id}/links/{link_id}/highlights` with form data. The response updates the highlights list (sidebar) and triggers a re‑application of visual marks.
- **Visual marks**: Saved highlights appear as `<mark>` elements inside the article text. The colour corresponds to the chosen colour (with default yellow). Marks are reapplied on page load and after any highlight addition/deletion.
- **Highlights panel** (below the article or in a sidebar):
  - Lists all highlights for this link, each showing:
    - Quoted text (`<blockquote>`)
    - Annotation (if any)
    - Colour (a small swatch can be shown)
    - “Remove” button → `DELETE /projects/{project_id}/links/{link_id}/highlights/{highlight_id}`. On success, the highlight item is removed from the panel and the corresponding `<mark>` is cleared and reapplied.
  - Empty state: “Select any text above to save it as a highlight.”
- **Persistent marks**: Highlights are stored with `start_offset` and `end_offset`. On page load, the frontend reads the highlight data from the panel (data attributes `data-start-offset`, `data-end-offset`, `data-color`) and wraps the text in `<mark>` elements. The same happens after any HTMX swap that updates the `#highlights-list` element.

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
2. Browse results, click “Save” on interesting links.
3. Switch to **Links** tab – see saved links with extraction status.
4. When status becomes “Completed”, click title → Reader page.
5. Read the article, highlight important passages (pick colour), add annotations.
6. Click “+ Add note about this” → return to project with source pre‑selected.
7. Write a note synthesising the information. It automatically links back to the source.
8. Add tags to both notes and links for organisation.

### 4.4 Searching and Filtering

1. Use the project search box to find terms across notes and links.
2. Click any tag badge to filter all items with that tag.

---

## 5. Global Interactions

### 5.1 Highlights (already described in Reader)

- Popup: appears on mouseup after text selection, disappears on click outside or save.
- Offsets: computed correctly against the entire raw article text.
- Colour selection: swatch click sets hidden input and submits form.
- Visual feedback: instant wrapping of the selection with the chosen colour after successful save; full marks reapplied after list update.

### 5.2 Tag Filtering

- Clicking any tag (in notes list, links list, tags tab) sends `GET /projects/{project_id}/tags/{tag_id}/items`.
- Response: HTML fragment listing all notes and links with that tag, each with a type badge (“Note” / “Link”) and a link to the item (note: in‑line; link: opens reader).
- Results are displayed in a dedicated area (`#tag-filter-results`) above the tabs (or inside a panel). The area can be cleared with a “Clear filter” button.
- No page reload: the tabs remain intact.

### 5.3 Full‑Text Search (Collected)

- Input in the project page triggers a debounced search (500ms after typing) or on form submit.
- `GET /projects/{project_id}/search-collected?q=...` returns an HTML fragment with a unified list of matching notes and links, ordered by relevance. Each result shows type, title, snippet, and a link.
- Results replace the content of `#collected-search-results` (below the search box).

### 5.4 Web Search

- `POST /projects/{project_id}/search/web` (or GET) with `query` parameter.
- Returns HTML fragment with search results and “Save” buttons.

---

## 6. API Interactions Summary

All UI routes (endpoints returning HTML) use the same backend service layer as the REST API. The frontend developer can reuse the existing API entirely; the following endpoints are relevant for UI rendering:

- `GET /dashboard` – dashboard page
- `POST /dashboard/projects` – create project (HTMX)
- `GET /projects/{project_id}` – project detail page
- `GET /projects/{project_id}/notes/list` – notes list fragment
- `POST /projects/{project_id}/notes` – create note
- `GET /projects/{project_id}/notes/{note_id}/edit` – edit note form fragment
- `PUT /projects/{project_id}/notes/{note_id}` – update note
- `DELETE /projects/{project_id}/notes/{note_id}` – delete note
- `POST /projects/{project_id}/notes/{note_id}/tags` – attach tag(s)
- `DELETE /projects/{project_id}/notes/{note_id}/tags/{tag_id}` – detach tag
- `GET /projects/{project_id}/links/list` – links list fragment
- `POST /projects/{project_id}/links/save` – save link from search
- `DELETE /projects/{project_id}/links/{link_id}` – delete link
- `GET /projects/{project_id}/links/{link_id}/read` – reader page
- `POST /projects/{project_id}/links/{link_id}/highlights` – create highlight
- `DELETE /projects/{project_id}/links/{link_id}/highlights/{highlight_id}` – delete highlight
- `POST /projects/{project_id}/search/web` – web search results
- `GET /projects/{project_id}/search/collected` – full‑text search results
- `GET /projects/{project_id}/tags/list` – tag list fragment
- `POST /projects/{project_id}/tags` – create tag
- `DELETE /projects/{project_id}/tags/{tag_id}` – delete tag
- `GET /projects/{project_id}/tags/{tag_id}/items` – tag‑filtered items

All these routes are protected and require a valid session (cookie). They also enforce project ownership (only the owner of the project can access its data).
