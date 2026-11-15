# Feature Specification: Next.js Frontend (Minimal App Router + Tailwind)

**Feature Branch**: `001-nextjs-frontend`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Add a minimal Next.js App Router and Tailwind CSS frontend in a new
`/frontend` directory. Preserve the functional requirements and information architecture of
`UI-SPEC.md` while applying the `design-taste-frontend` skill to improve the visual design and
avoid generic AI-generated UI patterns. Port the existing JavaScript API calls and state
management rather than inventing new backend functionality. Do not modify the existing `/app`
Python directory; the only backend touchpoint is updating `main.py` CORS to allow the frontend.
Preserve existing backend API behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign in and stay signed in (Priority: P1)

A researcher registers or logs in once, reaches their dashboard, moves between workspace pages
without re-authenticating, and can log out at any time.

**Why this priority**: Every other capability is gated on an authenticated session; without this
journey the product delivers no value.

**Independent Test**: Register a fresh account → land on the dashboard → navigate across pages and
refresh → still authenticated → log out → a protected page redirects to login.

**Acceptance Scenarios**:

1. **Given** no valid session, **When** I visit a protected page, **Then** I am redirected to the login page.
2. **Given** valid credentials, **When** I log in, **Then** I land on the dashboard and the session persists across navigation and refresh.
3. **Given** wrong credentials, **When** I submit the login form, **Then** an inline error ("Invalid email or password.") appears and the form input is preserved.
4. **Given** mismatched or shorter-than-8-characters passwords on the register form, **When** I submit, **Then** client-side errors appear without a request; **given** an already-registered email, **Then** the server's conflict error appears inline.
5. **Given** an authenticated session, **When** I log out, **Then** the session is destroyed and protected pages redirect to login.

---

### User Story 2 - Manage research projects (Priority: P1)

A researcher creates projects from the dashboard, sees all their projects with descriptions and
creation dates, and opens a project workspace — all without the page reloading unexpectedly.

**Why this priority**: Projects are the container for all other content; this is the second gate
to any real usage.

**Independent Test**: Create a project from the dashboard and confirm it appears immediately,
then open it and land in its workspace.

**Acceptance Scenarios**:

1. **Given** an empty account, **When** I load the dashboard, **Then** an empty state invites me to create my first project.
2. **Given** a name (and optional description), **When** I submit the create form, **Then** the new project card appears immediately, the form resets, and no full page reload occurs.
3. **Given** existing projects, **When** I load the dashboard, **Then** each project shows its name, description (or default text), and creation date, and clicking one opens its workspace.
4. **Given** a project I do not own (or a non-existent ID), **When** I open its URL, **Then** I see a clear not-found/forbidden message with a way back, never another user's data.

---

### User Story 3 - Write and organize notes (Priority: P1)

Inside a project, a researcher creates notes (optionally linked to a saved source link), edits
them inline, deletes them with confirmation, and attaches/detaches tags — with the list staying
current after every action and no full page reloads.

**Why this priority**: Note capture is the core daily workflow of the product.

**Independent Test**: In a project with at least one saved link, create a note with a source
link, edit it, attach and detach a tag, then delete it — each action reflected immediately.

**Acceptance Scenarios**:

1. **Given** the Notes tab, **When** I submit a title (content and source link optional), **Then** the note appears in the list and the form resets.
2. **Given** saved links exist, **When** I open the source-link selector, **Then** all of the project's links are selectable; **given** I arrived from the reader's "Add note about this", **Then** that link is preselected.
3. **Given** a listed note, **When** I click Edit, **Then** an inline prefilled form appears; saving updates the note in place; cancel restores the previous view.
4. **Given** a listed note, **When** I delete it and confirm, **Then** it disappears from the list.
5. **Given** a note, **When** I attach a tag from the picker or detach one via its badge, **Then** the note's tags update immediately without a reload.
6. **Given** an empty project, **When** the Notes tab loads, **Then** a loading placeholder shows while fetching and a helpful empty state shows when there are no notes.

---

### User Story 4 - Search the web and save links (Priority: P1)

A researcher runs a web search inside a project, saves promising results to the project, and
watches saved links progress from extraction pending to completed, then opens them to read.

**Why this priority**: Collecting sources is the other half of the core research loop.

**Independent Test**: Run a search, save one result, switch to the Links tab and confirm the
saved link appears with its extraction status, and that the status updates to "Completed"
without manually refreshing.

**Acceptance Scenarios**:

1. **Given** the Web Search tab, **When** I submit a query, **Then** results show title (opening the original in a new tab), snippet, and search engine.
2. **Given** a search result, **When** I click Save, **Then** the link is added to the project, a "Saved" confirmation appears, and it shows up in the Links tab.
3. **Given** a search returns nothing, **Then** I see "No results found."; **given** the search service is unreachable, **Then** I see "SearXNG is unavailable." — never a blank area.
4. **Given** a link with extraction pending, **When** extraction finishes, **Then** its status badge becomes "Completed" without me refreshing (preserving the current auto-update behavior).
5. **Given** a listed link, **When** I delete it and confirm, **Then** it disappears from the list.

---

### User Story 5 - Read and highlight articles (Priority: P2)

A researcher opens a saved article in the reader, reads the extracted text, selects passages to
save as colored, optionally annotated highlights, manages highlights, and jumps back into
note-taking about the article.

**Why this priority**: The reader with highlights is the product's signature interaction, but it
depends on links already being saved (User Story 4).

**Independent Test**: Open a completed link, select text, save a yellow highlight, refresh the
page and confirm the mark persists, then remove it and confirm the mark clears.

**Acceptance Scenarios**:

1. **Given** a completed link, **When** I open the reader, **Then** I see the title, source URL (new tab), extracted content, and a back link to the project.
2. **Given** a link whose extraction is not complete, **When** I open the reader, **Then** I see "Content not yet extracted." instead of content.
3. **Given** selected article text, **When** I release the selection, **Then** a popup appears with an optional annotation field, six color swatches (yellow, blue, green, orange, purple, grey), Save, and close; clicking outside dismisses it.
4. **Given** a saved highlight, **Then** the exact selected passage is wrapped in a colored mark (default yellow), instant visual feedback follows a successful save, and every saved highlight reappears as a mark after reload or any highlights update.
5. **Given** the highlights panel, **Then** each highlight shows its quoted text, annotation (if any), color, and a Remove action (with confirmation) that deletes it and clears its mark; with none, an empty state explains how to create one.
6. **Given** a save failure, **Then** an error shows inside the popup and the popup stays open (input not lost).
7. **When** I click "+ Add note about this", **Then** I return to the project's Notes tab with that link preselected as the source.

---

### User Story 6 - Find and reuse knowledge (Priority: P2)

A researcher searches across a project's notes and links, filters everything by a tag, and
exports the whole project as one Markdown file.

**Why this priority**: Retrieval and reuse is where accumulated research pays off; it depends on
content existing from User Stories 3 and 4.

**Independent Test**: Populate a project with tagged notes and links, run a full-text search, click
a tag badge to filter, clear the filter, and export the project.

**Acceptance Scenarios**:

1. **Given** the project search box, **When** I type and pause (~500 ms) or submit, **Then** a unified list of matching notes and links (type, title, snippet, link to the item) appears ordered by relevance; clearing the input clears the results.
2. **Given** any tag badge in the workspace, **When** I click it, **Then** a unified list of all notes and links with that tag (type badges, navigable items) appears above the tabs without a page reload, with a "Clear filter" action.
3. **Given** a tag filter with no matches, **Then** an empty result state is shown rather than a blank area.
4. **Given** a project with content, **When** I click export, **Then** one Markdown file containing notes, saved links, and highlights downloads.

---

### Edge Cases

- Reader opened while extraction is pending or failed → informational state, no crash; returning later shows content once completed.
- Highlights whose stored color is an unknown/legacy value (e.g., a raw hex from the old UI) → rendered as-is if valid, default yellow otherwise.
- Overlapping, adjacent, or out-of-order highlights → all render correctly; removing one leaves the others intact.
- Selection made inside an existing highlight or spanning multiple marks → still captured with correct global offsets.
- Very long article (100k+ characters) → highlight application must not freeze the page noticeably; marks applied in a single pass.
- Session expires mid-action (cookie max-age reached) → next API call returns 401, user is redirected to login with a message; no silent data loss shown as success.
- Backend unreachable / network offline → friendly "Something went wrong. Please try again." messages on actions; no unhandled crashes.
- Rate limited (429) on auth or AI-backed calls → clear "try again later" message honoring the server's guidance.
- Direct navigation to another user's project or a bad ID → not-found/forbidden view with navigation back, never leaked data.
- Tag deleted that is attached to notes/links → lists refresh consistently with server state.
- Note whose source link was deleted afterwards → note still displays and edits; source selector shows no stale selection.
- Search query with no characters → no request fired / results cleared (never an error state for an empty box).
- Duplicate project/tag/note submissions (double-click) → single creation; buttons disabled while a request is in flight.

## Requirements *(mandatory)*

### Functional Requirements

**Authentication**

- **FR-001**: The system MUST allow registration with email, password, and client-side password confirmation, surfacing validation errors (mismatch, minimum length) before any request and server errors (e.g., duplicate email) inline afterwards.
- **FR-002**: The system MUST allow login with valid credentials, show server-provided failures inline without clearing the form, and preserve the exact error-copy behavior of the current UI ("Invalid email or password.", "Something went wrong. Please try again.").
- **FR-003**: All authenticated pages MUST redirect to login when no valid session exists; successful login or registration MUST land the user on the dashboard with the session persisting across navigation and refresh.
- **FR-004**: A logout action MUST be available on every authenticated page and MUST terminate the session server-side (subsequent protected requests are rejected).

**Dashboard & projects**

- **FR-005**: The dashboard MUST list projects with name, description (or "No description yet." equivalent), and creation date, and MUST show the current empty state copy when there are none.
- **FR-006**: Project creation (required name, optional description) MUST complete without a full page reload: the new project appears immediately and the form resets on success.
- **FR-007**: Selecting a project MUST open its workspace; access to other users' projects MUST fail with a clear not-found/forbidden view.

**Project workspace**

- **FR-008**: The workspace MUST present back-navigation, project title/description, and exactly four tabs — Notes, Links, Web Search, Tags — switched client-side without reloads, defaulting to Notes.
- **FR-009**: A URL hash selecting a tab (e.g., `#notes-panel`) MUST activate that tab on load; arriving with a preselected source link MUST open Notes with that link preselected in the note form.
- **FR-010**: Every workspace action MUST update in place (no full page reloads) and MUST show a loading state while data is being fetched.

**Notes**

- **FR-011**: Notes MUST be creatable with a required title, optional content, and optional source link chosen from the project's saved links; success appends the note to the list and resets the form.
- **FR-012**: The notes list MUST show each note's title, content preview (truncated, with an explicit empty-content indicator), source link (navigating to the reader), and attached tags.
- **FR-013**: Notes MUST support inline edit (prefilled, save/cancel) and delete with confirmation, both reflected in the list immediately on success.
- **FR-014**: Notes MUST support attaching a tag from a picker of the project's tags and detaching a tag via its badge, with the note's tags updating immediately.

**Links & web search**

- **FR-015**: The links list MUST show each link's title (opens the reader), truncated URL (opens the original in a new tab), extraction status badge (Pending/Completed/Failed), tags, and a confirmed delete.
- **FR-016**: While any link's extraction is pending, the list MUST refresh automatically so the badge turns "Completed" without user action (preserving current behavior).
- **FR-017**: Web search MUST return results showing title (opens in new tab), snippet, and engine, with a per-result Save action that adds the link to the project, confirms success ("Saved"), and makes it appear in the links list.
- **FR-018**: Search MUST distinguish the outcomes: results, "No results found.", and "SearXNG is unavailable." on service failure.

**Tags**

- **FR-019**: Tags MUST be creatable (unique per project, server conflict shown inline), listable, and deletable with confirmation matching current copy; the tag list updates without reloads.
- **FR-020**: Clicking ANY tag badge in the workspace MUST display a unified list of the project's notes and links carrying that tag (with type badges and navigation to each item) above the tabs, without a page reload, with a "Clear filter" action and an empty-result state.

**Search & export**

- **FR-021**: Full-text search MUST trigger ~500 ms after typing stops or on submit, showing a unified relevance-ordered list of notes and links (type, title, snippet, link to item); clearing the input clears results.

**Reader & highlights**

- **FR-022**: The reader MUST show title, source URL (new tab), back-navigation, and either the extracted content or "Content not yet extracted.", plus a "+ Add note about this" action that returns to the Notes tab with the link preselected.
- **FR-023**: Selecting article text MUST open a popup with optional annotation, six color swatches (yellow, blue, green, orange, purple, grey), Save, and close; it dismisses on outside click and shows save errors inline without losing input.
- **FR-024**: Saved highlights MUST render as colored marks over the exact selected passage (default yellow), give instant visual feedback on save, reappear after every reload or list update from stored offsets, and support removal (with confirmation) that deletes the highlight and clears its mark.
- **FR-025**: The highlights panel MUST list every highlight with quoted text, annotation (if any), color, and Remove, and MUST show an explanatory empty state when none exist.

**Cross-cutting**

- **FR-026**: Every mutation (create/edit/delete/save) MUST provide success or error feedback within one second of the server's response; failures MUST never appear as successes, and network failures MUST use friendly generic copy.
- **FR-027**: The UI MUST be fully operable by keyboard for primary flows, use visible labels above inputs (never placeholder-as-label), announce async results/errors to assistive technology, and meet WCAG AA contrast in both light and dark themes.
- **FR-028**: The UI MUST present a coherent visual system per the Design Direction below — one accent, one radius rule, one icon family, bundled fonts — across every screen, in both themes.
- **FR-029**: Unauthenticated or expired-session responses on API calls MUST route the user to login with an explanatory message rather than rendering broken screens.

### Key Entities

(All entities pre-exist in the backend; the frontend consumes them read/write via the existing API.)

- **Session**: authenticated identity carried by the existing cookie; gates all pages; created by login/register, destroyed by logout.
- **Project**: named container owned by one user (name, description, created date); parents notes, links, tags.
- **Note**: title + optional content + optional source link reference; carries attached tags; created/edited/deleted in the workspace.
- **SavedLink**: URL, title, snippet, search query origin, extraction status, extracted content; carries attached tags; read in the reader.
- **Tag**: project-scoped label; attachable to notes and links; used for unified filtering.
- **Highlight**: a saved selection on a link (selected text, optional annotation, start/end character offsets, color); rendered as marks in the reader.
- **SearchResult**: item returned by full-text project search (type note/link, title, snippet, relevance) or web search (title, url, snippet, engine).

### Feature Constraints (Stakeholder-Mandated)

- **C-1**: The entire frontend MUST be generated inside a new `/frontend` directory — nothing else in the repository layout is restructured.
- **C-2**: The existing `/app` Python directory MUST NOT be modified, with ONE explicit exception: `main.py`'s CORS configuration MUST be updated to allow the frontend's origin. No other backend file changes.
- **C-3**: Backend API behavior MUST be fully preserved (constitution Principles II and III): no new endpoints, no changed responses, no removed behavior. Existing consumers (HTMX UI, scripts) MUST be unaffected.
- **C-4**: The frontend MUST be built with Next.js App Router and Tailwind CSS (stakeholder's chosen stack), porting the existing JavaScript API calls and state-management behavior rather than re-inventing product logic or adding backend features to compensate.
- **C-5**: `UI-SPEC.md`'s functional requirements and information architecture MUST be preserved (same pages, tabs, and interactions); only the visual design is intentionally improved, following the `design-taste-frontend` skill — no blind redesign, no generic AI-generated UI patterns.

## Clarifications

### Session 2026-09-28

- **Q**: Should the Next.js port include the two saved-link controls that exist in the current HTMX UI but are never mentioned in UI-SPEC.md — the "Re-extract" button and the inline "View/Hide content" toggle? (Scope Boundaries) → **A**: Option B — keep UI-SPEC-only scope: neither control is ported; both endpoints simply remain supported and untouched for the HTMX UI.

### Scope Boundaries

**In scope**: the five UI-SPEC screens (login, register, dashboard, project workspace with four
tabs, reader with highlights), full auth lifecycle, and the cross-cutting design/state/a11y
requirements above; the single permitted CORS edit.

**Out of scope**: AI helper UIs (roadmap, explain, summarise, tag suggestions, semantic search),
reading-list statuses, bulk tagging, re-extract and inline "View content" toggles (explicitly
deferred per clarification); removal or modification of the existing HTMX UI;
deployment/container wiring for the frontend; any other backend change.

### Frontend Contract Compatibility (Mandatory)

The Next.js frontend is a port of the existing HTMX UI and **MUST consume every endpoint the
current UI consumes**, regardless of whether those endpoints appear in `API-SPEC.md`. The
following endpoints are used by the current JavaScript/HTMX frontend and **MUST remain fully
supported and used by the Next.js port where applicable**:

**HTML/HTMX endpoints (root path, `include_in_schema=False`):**

| Method + Path                                                   | Purpose                                     | Template(s) Using It                                                          |
| --------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------- |
| `POST /logout`                                                | Clear auth cookie, redirect to login        | `base.html` (form action)                                                   |
| `POST /dashboard/projects`                                    | Create project, return fragment or redirect | `dashboard.html`                                                            |
| `GET /projects/{project_id}`                                  | Full project detail page                    | (page navigation)                                                             |
| `GET /projects/{project_id}/notes/list`                       | Notes list fragment                         | `project_detail.html`, `notes/_edit_form.html`                            |
| `GET /projects/{project_id}/notes/{note_id}/edit`             | Inline note edit form                       | `notes/_note_item.html`                                                     |
| `PUT /projects/{project_id}/notes/{note_id}`                  | Update note, return updated item            | `notes/_edit_form.html`                                                     |
| `DELETE /projects/{project_id}/notes/{note_id}`               | Delete note                                 | `notes/_note_item.html`                                                     |
| `GET /projects/{project_id}/notes/{note_id}/tags/available`   | Available tags picker for a note            | `notes/_note_item.html`, `notes/_tag_picker.html`                         |
| `POST /projects/{project_id}/notes/{note_id}/tags`            | Attach tag to note                          | `notes/_tag_picker.html`                                                    |
| `DELETE /projects/{project_id}/notes/{note_id}/tags/{tag_id}` | Detach tag from note                        | `notes/_note_item.html`                                                     |
| `GET /projects/{project_id}/links/list`                       | Links list fragment                         | `project_detail.html`                                                       |
| `GET /projects/{project_id}/links/{link_id}`                  | Single link fragment (poller)               | `links/_link_item.html` (hx-trigger load delay:3s)                          |
| `GET /projects/{project_id}/links/{link_id}/content`          | Extracted content inline view               | `links/_link_item.html`                                                     |
| `POST /projects/{project_id}/links/{link_id}/extract`         | Trigger re-extraction                       | `links/_link_item.html`                                                     |
| `DELETE /projects/{project_id}/links/{link_id}`               | Delete link                                 | `links/_link_item.html`                                                     |
| `POST /projects/{project_id}/search/web`                      | Web search results fragment                 | `project_detail.html`                                                       |
| `POST /projects/{project_id}/links/save`                      | Save search result as link                  | `search/_web_results.html`                                                  |
| `GET /projects/{project_id}/search/collected`                 | Full-text search results fragment           | `project_detail.html`                                                       |
| `GET /projects/{project_id}/tags/list`                        | Tags list fragment                          | `project_detail.html`                                                       |
| `POST /projects/{project_id}/tags`                            | Create tag                                  | `project_detail.html`                                                       |
| `DELETE /projects/{project_id}/tags/{tag_id}`                 | Delete tag                                  | `tags/_tag_item.html`                                                       |
| `GET /projects/{project_id}/tags/{tag_id}/items`              | Unified tag-filtered items                  | `links/_link_item.html`, `notes/_note_item.html`, `tags/_tag_item.html` |

**JSON API endpoints under `/api/v1` (missing from API-SPEC.md but implemented with auth/ownership):**

| Method + Path                                                                      | Purpose                    |
| ---------------------------------------------------------------------------------- | -------------------------- |
| `GET /api/v1/projects/{project_id}/links/{link_id}/highlights`                   | List highlights for a link |
| `POST /api/v1/projects/{project_id}/links/{link_id}/highlights`                  | Create highlight           |
| `DELETE /api/v1/projects/{project_id}/links/{link_id}/highlights/{highlight_id}` | Delete highlight           |

These three highlight endpoints are already implemented in `app/api/v1/links.py` with full
authentication and ownership checks but are undocumented in `API-SPEC.md` — they are part of the
frontend contract and the Next.js port MUST use them.

**No new endpoints will be created.** No existing endpoint behavior will change. The sole
backend modification is the CORS origin addition in `main.py` (Constraint C-2).

**Acceptance implication**: every endpoint in the two tables above MUST be exercised by the
port's E2E or integration tests to prove continued support.

### Design Direction

**Design read**: Reading this as a redesign-preserve of a self-hosted research tool for a solo
researcher — a calm, Linear-style product language, leaning on Tailwind utilities with a neutral
palette, one locked accent, and restrained motion.

**Dials** (skill §1, redesign-preserve baseline): `DESIGN_VARIANCE: 5` · `MOTION_INTENSITY: 3` ·
`VISUAL_DENSITY: 6`.

**Architecture (boundary level)**: Pages mirror the UI-SPEC route map one-to-one (`/login`,
`/register`, `/dashboard`, `/projects/{id}`, reader route). All data flows exclusively through
the documented JSON API with credentialed requests; the frontend holds no business rules —
authorization, validation, and limits remain server-side, and client checks are UX mirrors of
server rules only. State is scoped to what a screen needs (auth status, active tab, lists,
in-flight flags); nothing reads or stores the auth token in JavaScript (cookie only, per the
constitution).

**Typography**: A single bundled sans family for UI (Geist preferred — loaded through the
framework's font pipeline, never a runtime font-CDN link) plus its mono companion for metadata,
URLs, IDs, and status text. The reader's article body MAY use a serif reading face — the one
sanctioned serif, preserving the current long-form reading feel; serif is banned everywhere else.
Hierarchy is expressed through weight and color, not oversized display type (product UI, not a
landing page). Labels always sit above inputs; prose caps at ~65 characters.

**Color**: One neutral temperature (zinc/stone family) across the app; exactly ONE accent color,
locked app-wide. Status colors (success/warning/danger) and the six highlight colors are
functional data colors explicitly exempt from the accent lock. Banned: AI-purple gradients and
glows, oversaturated accents, pure `#000000`/`#ffffff` (use off-black/near-white), any
glassmorphism. Light and dark themes both ship, defaulting to system preference, with equal
visual hierarchy and AA contrast in each.

**Shape & spacing**: One corner-radius token for all controls and cards (e.g., 8–10 px), with
pills allowed ONLY for tag chips and status badges (documented exception, matches current
badges). A single spacing scale (4 px base) for gaps and padding; content grids (project cards,
result lists) use responsive CSS grid, never percentage flex math; the reader column stays ~70ch;
every multi-column section declares an explicit single-column collapse below 768 px.

**Components**: A small shared kit — button, input, select, tab, badge/chip, card, empty state —
used everywhere so intent maps to one style per label ("Save" never looks different twice).
Every interactive element ships its full state cycle: hover, focus-visible ring, pressed (1 px
tactile nudge or 0.98 scale), disabled, and in-flight. Loading states are shaped placeholders
matching the final layout, not bare spinners. Empty states use the existing copy from UI-SPEC.
Errors render inline, below the field they belong to.

**Icons**: One established icon family (Phosphor preferred) at a uniform stroke weight; no
hand-rolled SVG glyphs; no emoji used as UI icons (existing ←/+/× text glyphs are replaced by
family glyphs).

**Motion**: Transform/opacity transitions only, ≤200 ms, ease-out; `prefers-reduced-motion`
disables all non-essential motion. No scroll hijacking, no decorative infinite loops, no
`window.scrollY`-driven animation.

**Anti-slop rules (per skill §9)**: no purple/blue glow gradients; no Inter-as-default; no
placeholder-as-label; no three identical feature cards; no custom cursors; no z-index spam
(documented scale only); no em-dash flourishes or AI-cute microcopy — every visible string is
plain, functional, and grammatical; no invented precision numbers in copy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can go from landing on the app to creating a project and writing their first note in under 2 minutes following only on-screen cues.
- **SC-002**: 100% of the user flows in UI-SPEC §4 pass end-to-end acceptance on both desktop and mobile-width viewports.
- **SC-003**: Zero backend regressions — the existing automated test suite passes unchanged after the feature, and every API-SPEC endpoint behaves identically (verified before/after).
- **SC-004**: Full-text search results appear within 1 second after the user stops typing on a local deployment (500 ms debounce + response).
- **SC-005**: Highlight round-trip (select → save → visible colored mark) completes with no perceptible delay (<300 ms locally), and 20/20 tested highlights across all six colors persist correctly across reloads.
- **SC-006**: The primary flow (login → create project → create note → web search → open reader → save highlight) is completable keyboard-only; automated accessibility scans report 0 WCAG AA contrast failures in both themes.
- **SC-007**: 100% of tested mutations show success or error feedback within 1 second of the server response; no silent failures observed in the mutation test matrix.
- **SC-008**: Design review of all five screens finds zero banned patterns (purple-gradient hero, pure black/white surfaces, placeholder-as-label, mixed radius systems, emoji-as-icon, Inter-only type).

## Assumptions

- **Existing JavaScript source**: `./static/js/` does not exist in this repository. The actual
  client behavior lives in inline scripts (`login.html`, `register.html`, `project_detail.html`,
  `links/read.html`) plus HTMX attribute interactions in `app/templates/`; these were analyzed and
  are the porting source of truth (auth fetch + error copy + token handling, tab switching +
  hash activation, highlight selection/offset/marks engine, form reset-on-success, confirms,
  debounced search, auto-refresh while extracting).
- **Auth transport**: the existing httpOnly, SameSite=Lax cookie set by login/register is the
  session mechanism; requests are credentialed; the current localStorage token fallback in the
  old scripts is deliberately NOT ported (constitution: the frontend must never read or store the
  token in JavaScript).
- **Logout** uses the existing root logout route (clears the cookie); no new endpoint is created.
- **Dashboard header email display is deferred**: no identity/me endpoint exists and `/app` is
  frozen except CORS, so the authenticated header shows the logout action without the user's
  email (documented deviation from UI-SPEC §3.3, recoverable by a future additive API feature).
- **Tag filtering** is satisfied from existing list payloads (notes and links both carry their
  tags) — no new backend endpoint; results and Clear-filter behavior match UI-SPEC §5.2.
- **Extraction auto-refresh** is preserved by re-checking link status while anything is pending
  (equivalent to the current 3-second refresh), not by new backend machinery.
- **Highlights**: the frontend uses the JSON highlight endpoints under `/api/v1` (already
  implemented with auth/ownership); their absence from API-SPEC's highlights section is a
  pre-existing documentation gap to fix when this feature's docs are updated (constitution
  Principle VIII).
- **CORS**: the frontend's development origin is added to the allowlist in `app/main.py` — the
  sole sanctioned backend edit (C-2); the existing 4200 origins remain untouched.
- **Both UIs coexist**: the HTMX UI stays served and unmodified during and after this feature;
  no removal decision is made here (constitution Principle II).
- **Existing development environment**: the backend and all supporting services (PostgreSQL,
  Redis, SearXNG, Celery worker) are already running as Docker Compose services via the existing
  `docker-compose.yml`, with the `app` service bind-mounting the repository root at `.:/app`.
  These containers MUST NOT be created, replaced, or restructured. The Next.js frontend MUST NOT
  be added as a Docker service — it runs separately on the host from `/frontend` with `npm run dev`. During local development, the frontend communicates with the backend at
  `http://localhost:8000` (the exposed API port). The Docker Compose file remains unchanged except
  for the already-permitted CORS origin addition in `main.py`. The bind mount means `/frontend`
  is visible inside the `app` container, but the backend MUST NOT be modified to serve or build
  the Next.js frontend (constitution Principle VI). Treat the existing Docker services as
  already-running infrastructure required by current backend/API behavior.
- **Frontend API base URL**: during local development the frontend targets `http://localhost:8000`
  for all API calls; this URL is injected via a frontend environment variable, not hard-coded
  (per constitution: browser-visible configuration limited to public values).
- **Both themes ship** (light defaulting to system preference) per the design skill's dark-mode
  mandate; a theme toggle is optional polish, not required for acceptance.
