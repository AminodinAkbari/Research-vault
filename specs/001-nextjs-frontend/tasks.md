---
description: "Task list for Next.js frontend port (001-nextjs-frontend)"
---

# Tasks: Next.js Frontend (Minimal App Router + Tailwind)

**Input**: Design documents from `/specs/001-nextjs-frontend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec explicitly mandates them: "every endpoint in the two tables
[MUST] be exercised by the port's E2E or integration tests to prove continued support"
(spec §Frontend Contract Compatibility) and SC-006/SC-003 reference automated checks.

**Organization**: Tasks grouped by user story (US1–US6 from spec.md) so each story can be
implemented, tested, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in every task

## Path Conventions

- **Web app**: backend at repo root (`app/`), frontend at `frontend/` (per plan.md Structure Decision)
- All new frontend code under `frontend/`; sole backend edit is `app/main.py` (CORS, Constraint C-2)
- E2E tests: `frontend/tests/e2e/`; unit tests: `frontend/tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for `frontend/`

- [X] T001 Scaffold Next.js 14 App Router + TypeScript (strict) project in `frontend/` (package.json, tsconfig.json, next.config.js, src/app/layout.tsx, src/app/page.tsx)
- [X] T002 Install core dependencies in `frontend/package.json` per plan.md: next, react, tailwindcss@3.4, zod, @tanstack/react-query, motion, @phosphor-icons/react, date-fns, vitest, @playwright/test, typescript
- [X] T003 [P] Configure Tailwind CSS v3.4 in `frontend/tailwind.config.ts` + create `frontend/src/app/globals.css`
- [X] T004 [P] Configure linting and formatting in `frontend/.eslintrc.js` and `frontend/.prettierrc` (Next.js + TypeScript rules)
- [X] T005 [P] Create env template `frontend/.env.example` with `NEXT_PUBLIC_API_BASE=http://localhost:8000` and extend `frontend/.gitignore` (node_modules, .next, .env.local)
- [X] T006 [P] Configure Vitest in `frontend/vitest.config.ts` with jsdom environment and setup file `frontend/tests/setup.ts`
- [X] T007 [P] Configure Playwright in `frontend/playwright.config.ts`: baseURL http://localhost:3000, webServer `npm run dev`, tests in `frontend/tests/e2e/`
- [X] T008 [P] Load Geist Sans + Geist Mono via next/font (never a font-CDN link) in `frontend/src/app/layout.tsx` per research.md decision

**Checkpoint**: `npm run dev` starts; `npm run lint`, `npm run test` (empty) pass

**Phase 1 Complete**: T001–T008 all marked [X]

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CORS, typed API layer, design system, providers — MUST complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 Add frontend dev origins to CORS allowlist in `app/main.py` (append `"http://localhost:3000"` and `"http://127.0.0.1:3000"` to the existing `origins` list; leave the 4200 origins untouched; no other backend file may change)
- [X] T010 [P] Create Zod schemas + TS types in `frontend/src/lib/types.ts` copied from `specs/001-nextjs-frontend/contracts/types.ts` (Project, Note, SavedLink, Tag, Highlight, SearchResult, auth, error envelope)
- [X] T011 [P] Create endpoint path/verb map in `frontend/src/lib/endpoints.ts` from `specs/001-nextjs-frontend/contracts/api-endpoints.md`
- [X] T012 Create typed API client in `frontend/src/lib/api.ts`: `apiFetch<T>()` with `credentials: 'include'`, parses Zod schemas, throws typed `ApiError(status, body)`, never logs or stores tokens (constitution: cookie only)
- [X] T013 [P] Define design tokens in `frontend/src/app/globals.css` + `frontend/tailwind.config.ts` per spec Design Direction: ONE neutral temperature (zinc), exactly ONE accent (locked app-wide), radius token 8–10px (pills ONLY for tag chips/status badges), 4px spacing scale, status colors (success/warning/danger) + six highlight colors exempt from accent lock, no pure #000000/#ffffff
- [X] T014 [P] Create Button component in `frontend/src/components/ui/Button.tsx` with full state cycle: hover, focus-visible ring, pressed (1px nudge or scale-98), disabled, in-flight (disabled while request pending)
- [X] T015 [P] Create Input component in `frontend/src/components/ui/Input.tsx`: visible label ABOVE input (never placeholder-as-label), error text BELOW input, gap-2 input block
- [X] T016 [P] Create Badge/TagChip components in `frontend/src/components/ui/Badge.tsx` (pill radius documented exception; status badge variants completed/pending/failed with existing UI colors)
- [X] T017 [P] Create Card component in `frontend/src/components/ui/Card.tsx` (elevation only where hierarchy demands; tinted shadows, no pure-black)
- [X] T018 [P] Create TabBar component in `frontend/src/components/ui/TabBar.tsx` with WAI-ARIA tablist roles, keyboard arrow navigation, aria-selected (parity with existing UI a11y)
- [X] T019 [P] Create EmptyState + LoadingSkeleton components in `frontend/src/components/ui/EmptyState.tsx` and `frontend/src/components/ui/LoadingSkeleton.tsx` (skeletons shaped like final layout — no bare spinners)
- [X] T020 [P] Create Toast provider in `frontend/src/components/providers/ToastProvider.tsx`: success/error feedback within 1s of server response (FR-026), aria-live announcements (FR-027)
- [X] T021 [P] Create ConfirmDialog in `frontend/src/components/ui/ConfirmDialog.tsx` (shared delete-confirm pattern; message passed per call site)
- [X] T022 [P] Create ThemeProvider in `frontend/src/components/providers/ThemeProvider.tsx`: light/dark, defaults to prefers-color-scheme, equal hierarchy + WCAG AA contrast both themes (SC-006)
- [X] T023 [P] Create QueryProvider in `frontend/src/components/providers/QueryProvider.tsx` (TanStack Query v5, cache invalidation for list refreshes)
- [X] T024 Create error helpers in `frontend/src/lib/errors.ts` (depends on T012): map status → user copy (401 → redirect login with "Session expired" message; 429 → "try again later" honoring Retry-After; network → "Something went wrong. Please try again.")
- [X] T025 Wire root layout in `frontend/src/app/layout.tsx`: ThemeProvider + QueryProvider + ToastProvider + Geist fonts (depends on T008, T020, T022, T023)
- [X] T026 [P] Create Icon wrapper in `frontend/src/components/ui/Icon.tsx` (Phosphor only, uniform stroke-width 1.5, aria-hidden; one icon family — no hand-rolled SVG, no emoji-as-icon)

**Checkpoint**: Foundation ready — user story implementation can now begin

**Phase 2 Complete**: T009–T026 all marked [X]

---

## Phase 3: User Story 1 - Sign in and stay signed in (Priority: P1) 🎯 MVP

**Goal**: Register/login once, persistent session across navigation/refresh, logout anywhere

**Independent Test**: Register fresh account → land on dashboard → navigate + refresh → still authenticated → log out → protected page redirects to login

### Tests for User Story 1 (included — spec mandates endpoint coverage)

> Write these FIRST; confirm they FAIL before implementation

- [X] T027 [P] [US1] Unit tests for apiFetch error paths + 401 redirect behavior in `frontend/tests/unit/api.test.ts`
- [X] T028 [P] [US1] E2E auth spec covering all 5 US1 acceptance scenarios (redirect-when-logged-out, login persists, wrong-credentials inline copy "Invalid email or password." with input preserved, register client validation mismatch/<8 chars + 409 inline, logout locks protected pages) in `frontend/tests/e2e/auth.spec.ts`

### Implementation for User Story 1

- [X] T029 [P] [US1] Create auth API functions in `frontend/src/lib/auth.ts`: register (POST /api/v1/auth/register), login (POST /api/v1/auth/login), logout (POST /logout — cookie clear, follow redirect to /login); credentials always included
- [X] T030 [P] [US1] Create useAuth hook in `frontend/src/hooks/useAuth.ts`: session state from cookie validity (probe authenticated endpoint), isAuthenticated, login/register/logout actions
- [X] T031 [US1] Build login page in `frontend/src/app/(auth)/login/page.tsx`: email + password, inline server-error display without clearing form, exact copy "Invalid email or password." / "Something went wrong. Please try again." (FR-002), redirect to /dashboard on success (FR-003), link to /register
- [X] T032 [US1] Build register page in `frontend/src/app/(auth)/register/page.tsx`: client-side checks — password mismatch and password minimum length 8 characters before any request (FR-001); server 409 conflict shown inline; redirect to /dashboard on success
- [X] T033 [P] [US1] Create LogoutButton in `frontend/src/components/layout/LogoutButton.tsx`: calls POST /logout, redirects to /login (FR-004)
- [X] T034 [US1] Create protected route layout in `frontend/src/app/(dashboard)/layout.tsx`: server-side session check; unauthenticated → redirect /login (FR-003, FR-029)
- [X] T035 [US1] Implement root redirect in `frontend/src/app/page.tsx`: authenticated → /dashboard, else → /login (parity with GET /)
- [X] T036 [US1] Build authenticated header in `frontend/src/components/layout/Header.tsx`: brand link + LogoutButton on every authenticated page (FR-004); no email display (spec Assumption: deferred)

**Checkpoint**: User Story 1 fully functional and testable independently — STOP and VALIDATE

**Phase 3 Complete**: T027–T036 all marked [X]

---

## Phase 4: User Story 2 - Manage research projects (Priority: P1)

**Goal**: Dashboard project list + create without reload + workspace shell with four tabs

**Independent Test**: Create project from dashboard → card appears immediately → open it → land in workspace with project header + four tabs

### Tests for User Story 2

> Write these FIRST; confirm they FAIL before implementation

- [X] T037 [P] [US2] E2E projects spec covering all 4 US2 acceptance scenarios (empty-state copy, create without reload + form resets, list shows name/description-or-default/date, non-owned/bad-ID → not-found view) in `frontend/tests/e2e/projects.spec.ts`

### Implementation for User Story 2

- [X] T038 [P] [US2] Create useProjects hook in `frontend/src/hooks/useProjects.ts`: list projects (GET /api/v1/projects), create project (POST /api/v1/projects with name 1–200 chars required, description optional max 2000), cache invalidation
- [X] T039 [US2] Build dashboard page in `frontend/src/app/(dashboard)/dashboard/page.tsx`: project list, empty state copy (FR-005), create form, header (FR-005, FR-006)
- [X] T040 [P] [US2] Create ProjectCreateForm in `frontend/src/components/forms/ProjectCreateForm.tsx`: required name (1–200 chars), optional description (max 2000), submit without full page reload, new card appears immediately, form resets on success, button disabled in-flight (FR-006, edge: double-click → single creation)
- [X] T041 [P] [US2] Create ProjectCard in `frontend/src/components/dashboard/ProjectCard.tsx`: name, description or "No description yet.", formatted created date, navigates to /projects/[id]
- [X] T042 [US2] Build project workspace shell in `frontend/src/app/(dashboard)/projects/[id]/page.tsx`: back-navigation "← Back to projects", project title/description via GET /api/v1/projects/{id}, exactly four tabs — Notes, Links, Web Search, Tags — default Notes, client-side switching without reload (FR-008); slots for search box, export button, tag-filter results (FR-008, FR-010)
- [X] T043 [P] [US2] Create NotFound view in `frontend/src/components/layout/NotFound.tsx`: clear not-found/forbidden message + way back, never leaked data (FR-007)
- [X] T044 [US2] Implement tab activation utilities in `frontend/src/lib/tabs.ts`: URL hash activates tab on load (e.g. #notes-panel), arriving with ?source_link_id=... opens Notes tab with link preselected (FR-009)

**Checkpoint**: US1 + US2 work independently; workspace shell ready for tab panels

**Phase 4 Complete**: T037–T044 all marked [X]

---

## Phase 5: User Story 3 - Write and organize notes (Priority: P1)

**Goal**: Notes CRUD + source-link selection + tag attach/detach + Tags tab — all in-place, no reloads

**Independent Test**: In a project, create a note with source link, edit it, attach and detach a tag, delete it — each reflected immediately; create/list/delete tags in Tags tab

### Tests for User Story 3

> Write these FIRST; confirm they FAIL before implementation

- [ ] T045 [P] [US3] E2E notes spec covering all 6 US3 acceptance scenarios (create resets form, source-link select + preselect from ?source_link_id, inline edit save/cancel, delete-with-confirm removes, tag attach/detach updates immediately, loading placeholder + empty state) in `frontend/tests/e2e/notes.spec.ts`

### Implementation for User Story 3

- [ ] T046 [P] [US3] Create useNotes hook in `frontend/src/hooks/useNotes.ts`: list/create/update/delete via /api/v1 notes endpoints; NoteCreate — title required 1–200 chars, content optional max 100000, source_link_id optional UUID; tag attach (tag_ids array) / detach (DELETE tags/{tag_id}); cache invalidation
- [ ] T047 [P] [US3] Create useTags hook in `frontend/src/hooks/useTags.ts`: list/create/delete via /api/v1 tags endpoints; TagCreate — name required 1–50 chars, unique per project (409 shown inline: 'A tag named "X" already exists in this project.')
- [ ] T048 [US3] Build NotesPanel in `frontend/src/components/notes/NotesPanel.tsx`: loading placeholder while fetching, empty state when no notes (FR-010, US3 scenario 6)
- [ ] T049 [P] [US3] Create NoteCreateForm in `frontend/src/components/notes/NoteCreateForm.tsx`: required title, optional content, source-link dropdown populated from project's links, preselect when ?source_link_id present (FR-011, FR-009); form resets on success
- [ ] T050 [P] [US3] Create NoteListItem in `frontend/src/components/notes/NoteListItem.tsx`: title, content preview truncated at 200 chars with ellipsis or "(No content)", source link navigates to reader, attached tag badges (FR-012)
- [ ] T051 [US3] Create NoteEditForm in `frontend/src/components/notes/NoteEditForm.tsx`: inline prefilled edit (title/content/source link), save updates in place, cancel restores previous view (FR-013)
- [ ] T052 [US3] Wire note delete in `frontend/src/components/notes/NoteListItem.tsx` with ConfirmDialog using exact copy "Delete this note? This cannot be undone."; list updates immediately (FR-013)
- [ ] T053 [US3] Create TagAttachPicker in `frontend/src/components/notes/TagAttachPicker.tsx`: available tags = project tags minus attached; select attaches immediately, badge × detaches immediately (FR-014)
- [ ] T054 [P] [US3] Build TagsPanel in `frontend/src/components/tags/TagsPanel.tsx`: create tag form, tags list, delete with confirm copy 'Delete tag "X"? It will be removed from all notes.'; list updates without reloads (FR-019)

**Checkpoint**: US3 fully functional (notes + tags management)

---

## Phase 6: User Story 4 - Search the web and save links (Priority: P1)

**Goal**: Web search → save results → links list with auto-updating extraction status → reader link

**Independent Test**: Run search, save result, switch to Links tab → saved link with Pending badge → badge becomes Completed without manual refresh; delete works

### Tests for User Story 4

> Write these FIRST; confirm they FAIL before implementation

- [ ] T055 [P] [US4] E2E search-links spec covering all 5 US4 acceptance scenarios (results show title/url-new-tab/snippet/engine, Save → "Saved" + appears in Links, "No results found." + "SearXNG is unavailable.", status auto-updates to Completed, delete-with-confirm removes) in `frontend/tests/e2e/search-links.spec.ts`

### Implementation for User Story 4

- [ ] T056 [P] [US4] Create useLinks hook in `frontend/src/hooks/useLinks.ts`: list/create (SavedLinkCreate — url valid max 2048, title 1–500 required, snippet, search_query)/delete via /api/v1 links endpoints
- [ ] T057 [P] [US4] Create useWebSearch hook in `frontend/src/hooks/useWebSearch.ts`: POST /api/v1/projects/{id}/search with query; map network/502 failure to copy "SearXNG is unavailable.", empty array → "No results found." (FR-018)
- [ ] T058 [US4] Build LinksPanel in `frontend/src/components/links/LinksPanel.tsx`: title → reader route, truncated URL (80 chars + ellipsis) → external new tab, extraction status badge (Pending/Completed/Failed), tag badges, delete with confirm copy "Delete this saved link?" (FR-015)
- [ ] T059 [US4] Implement extraction auto-refresh in `frontend/src/hooks/useExtractionPolling.ts`: while any link has extraction_status === 'pending', re-fetch links every ~3s (poll single-link GET /api/v1/projects/{id}/links/{link_id} or list); badge flips to Completed without user action (FR-016)
- [ ] T060 [US4] Build WebSearchPanel in `frontend/src/components/search/WebSearchPanel.tsx`: query form, results list (title opens original in new tab, snippet, engine badge), per-result Save button → success "Saved" confirmation + link appears in Links tab; empty/error states distinct (FR-017, FR-018)

**Checkpoint**: US4 fully functional (collect half of research loop)

---

## Phase 7: User Story 5 - Read and highlight articles (Priority: P2)

**Goal**: Reader page with extracted content, selection → colored annotated highlights that persist, highlights panel management, jump back to notes

**Independent Test**: Open completed link → select text → save yellow highlight → refresh → mark persists → remove → mark clears

### Tests for User Story 5

> Write these FIRST; confirm they FAIL before implementation

- [ ] T061 [P] [US5] Unit tests for the highlight offset/mark algorithm port (text-node walker, cumulative offsets, descending-order application, overlapping/adjacent/out-of-order ranges, invalid offset skip) in `frontend/tests/unit/highlight-offsets.test.ts` — port behavior from `app/templates/links/read.html`
- [ ] T062 [P] [US5] E2E reader-highlights spec covering all 7 US5 acceptance scenarios (completed reader content, "Content not yet extracted." for pending, selection popup with 6 swatches + Save/close + outside-click dismiss, marks persist across reload + instant feedback, panel list w/ confirm remove + empty state, save failure keeps popup + inline error, "+ Add note about this" preselects source) in `frontend/tests/e2e/reader-highlights.spec.ts`

### Implementation for User Story 5

- [ ] T063 [P] [US5] Create useHighlights hook in `frontend/src/hooks/useHighlights.ts`: GET/POST/DELETE via the three undocumented JSON endpoints /api/v1/projects/{id}/links/{link_id}/highlights[/{highlight_id}] (contract H1–H3); HighlightCreate — selected_text required min 1, start_offset >= 0, end_offset > start_offset, color optional
- [ ] T064 [US5] Port highlight marks engine to `frontend/src/lib/highlightMarks.ts` + hook `frontend/src/hooks/useHighlightMarks.ts`: TreeWalker over article text nodes, cumulative start positions, sort highlights by start_offset descending, re-wrap via Range.surroundContents or manual node split, clearAllMarks + article.normalize() before re-apply, apply on mount and whenever highlights list changes; default color yellow (behavior parity with `app/templates/links/read.html`)
- [ ] T065 [P] [US5] Define highlight color constants in `frontend/src/lib/constants.ts`: yellow #fff59d, blue #b3e5fc, green #c8e6c9, orange #ffccbc, purple #e1bee7, grey #f0f0f0; legacy/unknown stored colors (e.g. raw hex) render as-is if valid, default yellow otherwise
- [ ] T066 [US5] Build reader page in `frontend/src/app/(dashboard)/projects/[id]/links/[linkId]/read/page.tsx`: back link "← Back to {project}", title, source URL opens new tab, extracted content or "Content not yet extracted.", "+ Add note about this" → /projects/{id}?source_link_id={link_id}#notes-panel (FR-022)
- [ ] T067 [US5] Create HighlightPopup in `frontend/src/components/reader/HighlightPopup.tsx`: appears on text selection (mouseup within article), optional annotation input, six color swatches (click = select + submit), Save button (defaults yellow), close button, outside-click dismiss; save error shows inline and popup stays open with input intact (FR-023, US5 scenario 6); instant temp-mark feedback on success
- [ ] T068 [P] [US5] Create HighlightsPanel in `frontend/src/components/reader/HighlightsPanel.tsx`: each highlight shows quoted text, annotation (if any), color swatch, Remove with confirm; empty state "Select any text above to save it as a highlight." (FR-025)

**Checkpoint**: US5 fully functional (reader + signature highlight interaction)

---

## Phase 8: User Story 6 - Find and reuse knowledge (Priority: P2)

**Goal**: Debounced full-text search, unified tag filtering with clear, project Markdown export

**Independent Test**: Populate project with tagged notes/links → run full-text search → click tag badge → filter results → clear filter → export downloads .md

### Tests for User Story 6

> Write these FIRST; confirm they FAIL before implementation

- [ ] T069 [P] [US6] E2E search-filter-export spec covering all 4 US6 acceptance scenarios (500ms-debounced results ordered by relevance + clear-input clears, tag badge → unified filtered list above tabs + "Clear filter" no reload, empty-result state, export downloads one Markdown file) in `frontend/tests/e2e/search-filter-export.spec.ts`

### Implementation for User Story 6

- [ ] T070 [P] [US6] Create useCollectedSearch hook in `frontend/src/hooks/useCollectedSearch.ts`: GET /api/v1/projects/{id}/search-collected?q=..., debounce ~500 ms after typing stops or on submit, empty query fires no request and clears results (FR-021, edge case)
- [ ] T071 [US6] Build ProjectSearchBox in `frontend/src/components/search/ProjectSearchBox.tsx`: unified relevance-ordered results (type badge note/link, title, snippet, navigable link to item), rendered in workspace slot above tabs (FR-021)
- [ ] T072 [US6] Implement tag filtering: TagFilterResults component in `frontend/src/components/tags/TagFilterResults.tsx` + wire tag-badge clicks across note/link/tag panels (client-side derivation from notes+links payloads per spec Assumption — no new endpoint): unified list with type badges + navigation, "Clear filter" action, empty-result state, displayed above tabs without page reload (FR-020)
- [ ] T073 [P] [US6] Create ExportButton in `frontend/src/components/export/ExportButton.tsx`: direct download link to GET /api/v1/projects/{id}/export/markdown (cookie auth accepted), one click → one .md file (US6 scenario 4), placed in workspace slot

**Checkpoint**: All six user stories independently functional

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and compliance affecting multiple user stories

- [ ] T074 [P] Verify endpoint contract coverage: confirm every endpoint the frontend calls is exercised by tests against the tables in `specs/001-nextjs-frontend/contracts/api-endpoints.md`; record gaps in test names, not new endpoints
- [ ] T075 [P] Run design review (SC-008) across all five screens in `frontend/src/app/` against the design-taste-frontend pre-flight: zero purple-gradient glows, no pure #000/#fff surfaces, no placeholder-as-label, one radius system + pill exception only, no emoji-as-icon, Geist (not Inter) typography, no invented precision numbers in copy
- [ ] T076 [P] Accessibility pass in `frontend/src/` (FR-027, SC-006): keyboard-only completion of primary flow (login → create project → create note → search → reader → highlight), visible labels/focus rings, aria-live for async results/errors, WCAG AA contrast verified in both themes
- [ ] T077 [P] Motion audit: all transitions transform/opacity only ≤200ms, prefers-reduced-motion disables non-essential motion, no scroll-hijack or decorative loops in `frontend/src/`
- [ ] T078 Production build performance check: `npm run build` in `frontend/`; initial JS bundle < 150 kB gzipped; smoke LCP/INP/CLS targets from plan.md
- [ ] T079 Backend regression: run `docker compose exec app pytest` (repo root) — full suite green (SC-003); spot-check HTMX UI five flows still work — login, dashboard, notes CRUD, search, reader (SC-009)
- [ ] T080 [P] Document the three JSON highlight endpoints (H1–H3) in `API-SPEC.md` under the Highlights section — closes the documentation gap noted in spec Assumptions (constitution Principle VIII)
- [ ] T081 [P] Record frontend/backend boundary + CORS decision (context, options, decision, consequences) in `ARCHITECTURE.md` (constitution Principle VIII; no `/app` code changes)
- [ ] T082 [P] Add frontend development section to `README.md` (npm run dev, env var, CORS note) alongside existing HTMX UI instructions
- [ ] T083 Run full validation guide in `specs/001-nextjs-frontend/quickstart.md`: prerequisites, setup, all six user-story manual/Playwright checks, lint, typecheck, unit + E2E suites green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — starts immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (T009 CORS also required before any browser fetch succeeds)
- **US1 (Phase 3)**: Depends on Foundational — auth guard required by every protected page
- **US2 (Phase 4)**: Depends on US1 (protected layout + session) 
- **US3 (Phase 5)**: Depends on US2 (workspace shell + tab frame)
- **US4 (Phase 6)**: Depends on US2 (workspace shell + tab frame)
- **US5 (Phase 7)**: Depends on US2 (project route space); full E2E needs a completed link (seed via US4 or API)
- **US6 (Phase 8)**: Depends on US2 (workspace shell); realistic filter data comes from US3/US4 content (seed in test)
- **Polish (Phase 9)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — independently testable
- **US2 (P1)**: US1 (needs authenticated session) — independently testable after US1
- **US3 (P1)**: US2 shell; source-link dropdown fetches links directly via Foundational API client (does NOT require US4 panels)
- **US4 (P1)**: US2 shell — independent of US3
- **US5 (P2)**: US2 shell; test fixture needs a completed link (seed via API if US4 not yet done)
- **US6 (P2)**: US2 shell; filter/search/export data fetched directly (independent of US3/US4 panels; seeded content for realistic E2E)

### Within Each User Story

- Tests first (must FAIL before implementation)
- Hooks/services before components
- Components before page wiring
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup**: T003–T008 parallel (different config files) after T001–T002
- **Foundational**: T010/T011 parallel; T013–T023 mostly parallel (one file each); T026 parallel
- **US1**: T027/T028 (tests) parallel; T029/T030/T033 parallel; login + register pages parallel after auth lib
- **US2**: T037 (test) then T038/T040/T041 parallel
- **US3**: T046/T047 parallel (hooks), T049/T050 parallel (components), T054 parallel
- **US4**: T056/T057 parallel (hooks), tests parallel
- **US5**: T061/T062 parallel (tests), T063/T065/T068 parallel
- **US6**: T070 parallel with test T069; T073 parallel
- **Cross-story**: after US2, US3 ∥ US4 ∥ US5 ∥ US6 possible (separate panel component files; coordinate on workspace page slot wiring)
- **Polish**: T074–T077, T080–T082 parallel

---

## Parallel Examples

```bash
# User Story 1 (launch together — separate files):
Task: "Unit tests for apiFetch in frontend/tests/unit/api.test.ts"
Task: "E2E auth spec in frontend/tests/e2e/auth.spec.ts"
Task: "auth lib in frontend/src/lib/auth.ts"
Task: "useAuth hook in frontend/src/hooks/useAuth.ts"
Task: "LogoutButton in frontend/src/components/layout/LogoutButton.tsx"

# User Story 3 (launch together — separate files):
Task: "useNotes hook in frontend/src/hooks/useNotes.ts"
Task: "useTags hook in frontend/src/hooks/useTags.ts"
Task: "NoteCreateForm in frontend/src/components/notes/NoteCreateForm.tsx"
Task: "NoteListItem in frontend/src/components/notes/NoteListItem.tsx"
Task: "TagsPanel in frontend/src/components/tags/TagsPanel.tsx"

# User Story 5 (launch together — separate files):
Task: "highlight offsets unit tests in frontend/tests/unit/highlight-offsets.test.ts"
Task: "useHighlights hook in frontend/src/hooks/useHighlights.ts"
Task: "color constants in frontend/src/lib/constants.ts"
Task: "HighlightsPanel in frontend/src/components/reader/HighlightsPanel.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `npm run test:e2e -- auth.spec.ts` passes; manual login/logout check
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. + US1 (auth) → test → deploy (MVP!)
3. + US2 (dashboard + workspace shell) → test → deploy
4. + US3 (notes + tags) → test → deploy — core note-taking works
5. + US4 (search + links) → test → deploy — full research loop works
6. + US5 (reader + highlights) → test → deploy — signature interaction
7. + US6 (search/filter/export) → test → deploy — retrieval complete
8. Polish → full quickstart.md validation → backend regression → PR

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Once US1 + US2 complete (sequential — auth then shell):
   - Developer A: US3 (notes)
   - Developer B: US4 (links/search)
   - Developer C: US5 (reader/highlights)
   - Developer D: US6 (search/filter/export)
3. Stories complete and integrate via shared workspace slots

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable; checkpoints mark validation points
- Commit after each task or logical group
- Backend constraints: `app/main.py` CORS is the ONLY backend change (C-2); `app/api/ui.py` and `app/api/ui_project.py` must not be modified; no new endpoints (C-3)
- No Docker service for frontend — `npm run dev` on host (spec Assumption: Existing development environment)
- Frontend must never read/store the auth token in JavaScript — cookie only (constitution Frontend/Backend Boundary)
