# Quickstart: Next.js Frontend Port

Validation guide for running and testing the frontend locally. Implementation details live in `tasks.md`; this document is a run/validation checklist.

---

## Prerequisites

| Requirement | Check | Notes |
|-------------|-------|-------|
| Docker + Docker Compose | `docker --version && docker compose version` | Backend services must run |
| Node.js 20+ (LTS) | `node --version` | For frontend dev server + build |
| pnpm or npm | `pnpm --version` or `npm --version` | Choose one for install scripts below |
| Backend running | `curl http://localhost:8000/health` | Returns `{"status": "ok"}` |
| API docs accessible | Open `http://localhost:8000/docs` | Swagger UI loads |

---

## Setup

### 1. Ensure backend services are running

```bash
# From repo root
docker compose up -d

# Verify all services healthy
docker compose ps
# Expected: app, db, redis, searxng, celery_worker — all "Up" or "running"
```

### 2. Start frontend

```bash
cd frontend

# Copy environment template
cp .env.example .env.local
# Verify: NEXT_PUBLIC_API_BASE=http://localhost:8000

# Install dependencies
pnpm install  # or: npm install

# Start dev server
pnpm dev  # or: npm run dev
# Expected: Next.js running at http://localhost:3000
```

### 3. Verify CORS

```bash
curl -I http://localhost:3000/login
# Should load the login page (HTML)

# Backend should now accept localhost:3000 origin
curl -I -H "Origin: http://localhost:3000" http://localhost:8000/api/v1/projects
# Should include: Access-Control-Allow-Origin: http://localhost:3000
```

---

## Validation Scenarios (User Stories)

Run each scenario manually or via Playwright (`pnpm test:e2e`).

### US1: Authentication (P1)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Visit `http://localhost:3000/` | Redirect to `/login` |
| 2 | Click "Register" | Navigate to `/register` |
| 3 | Submit mismatched passwords | Client-side error "Passwords do not match." — no request |
| 4 | Submit valid registration | Redirect to `/dashboard`; session cookie set |
| 5 | Refresh page | Still on `/dashboard` (session persists) |
| 6 | Submit wrong password on login | Inline error "Invalid email or password." — form preserved |
| 7 | Log out | Redirect to `/login`; visit `/dashboard` → redirected to `/login` |

**CLI check**: `pnpm test:e2e -- auth.spec.ts`

---

### US2: Project Management (P1)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Visit `/dashboard` (authenticated) | Empty state: "No projects yet..." |
| 2 | Enter name, click "Create" | Card appears immediately; form resets |
| 3 | Click project card | Navigate to `/projects/[id]` workspace |
| 4 | Direct URL to non-owned project | Not-found view with back navigation |

**CLI check**: `pnpm test:e2e -- projects.spec.ts`

---

### US3: Notes Workspace (P1)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open project → Notes tab (default) | Notes list loads with placeholder |
| 2 | Submit title only | Note appears in list; form resets |
| 3 | Submit with source link | Note shows "Source: [link title]" |
| 4 | Click Edit | Inline form prefilled; Save/Cancel |
| 5 | Click Delete + confirm | Note disappears from list |
| 6 | Attach tag from picker | Tag badge appears on note immediately |
| 7 | Click tag badge × | Tag removed immediately |

**CLI check**: `pnpm test:e2e -- notes.spec.ts`

---

### US4: Web Search & Save Links (P1)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Web Search tab → enter query → Search | Results with title, snippet, engine, "Save" |
| 2 | Click "Save" | "Saved" confirmation; link in Links tab with "Pending" badge |
| 3 | Wait ~3-10 seconds | Badge auto-changes to "Completed" (no manual refresh) |
| 4 | Click link title | Opens reader page |
| 5 | Delete link + confirm | Link disappears |
| 6 | Search returns nothing | "No results found." |
| 7 | Stop SearXNG → search | "SearXNG is unavailable." |

**CLI check**: `pnpm test:e2e -- search-links.spec.ts`

---

### US5: Reader & Highlights (P2)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open completed link in reader | Title, URL (new tab), extracted content, back link |
| 2 | Open pending link in reader | "Content not yet extracted." |
| 3 | Select text | Popup appears: annotation, 6 color swatches, Save, close |
| 4 | Click color + Save | Mark appears in selected color; highlight in panel |
| 5 | Refresh page | All marks persist |
| 6 | Remove highlight + confirm | Mark cleared; removed from panel |
| 7 | Click "+ Add note about this" | Returns to Notes tab with link preselected |
| 8 | Save failure (kill backend) | Error in popup; popup stays open |

**CLI check**: `pnpm test:e2e -- reader-highlights.spec.ts`

---

### US6: Search & Tag Filter & Export (P2)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Type in search box → pause 500ms | Unified results below (type, title, snippet) |
| 2 | Clear input | Results cleared |
| 3 | Click any tag badge (note/link/tag) | Filter results appear above tabs |
| 4 | Click "Clear filter" | Workspace restored |
| 5 | Click "Export" | Downloads `.md` file |

**CLI check**: `pnpm test:e2e -- search-filter-export.spec.ts`

---

## Lint / Type Check / Unit Tests

```bash
cd frontend

# ESLint + Prettier
pnpm lint  # or: npm run lint

# TypeScript strict check
pnpm typecheck  # or: npm run typecheck

# Unit tests (Vitest + RTL)
pnpm test  # or: npm run test
# Expected: all unit tests pass (components, hooks, utils, API layer)
```

---

## E2E Tests (Playwright)

```bash
cd frontend

# Ensure backend is running (see Prerequisites)
# Ensure frontend dev server is running OR let Playwright start it

pnpm test:e2e  # or: npm run test:e2e
# Expected: all user story specs pass
```

---

## Design Review Checklist (SC-008)

Manual or automated check across `/login`, `/register`, `/dashboard`, `/projects/[id]`, reader:

- [ ] No purple/blue glow gradients
- [ ] No pure `#000000` / `#ffffff` surfaces
- [ ] No `placeholder-as-label` patterns
- [ ] No mixed corner-radius systems (one radius + documented pill exception for badges/tags)
- [ ] No emoji-as-icon
- [ ] Geist Sans + Geist Mono used (not Inter)
- [ ] Both light and dark themes render with WCAG AA contrast
- [ ] Keyboard-only traversal of primary flow works (login → create project → create note → search → reader → highlight)

**Automated a11y**: `pnpm test:a11y` (if axe-core integration added) or manual pass.

---

## Backend Regression Check (SC-003, SC-009)

```bash
# From repo root — existing test suite must pass unchanged
docker compose exec app pytest
# Expected: all existing tests pass (auth, projects, notes, links, tags, search, highlights, UI)

# Spot-check HTMX UI still works
curl http://localhost:8000/login | head -20
# Returns login HTML

curl http://localhost:8000/dashboard -H "Cookie: <valid_token>"
# Returns dashboard HTML (or 303 if no cookie)
```

---

## Production Build (Optional)

```bash
cd frontend
pnpm build  # or: npm run build
pnpm start  # or: npm run start
# Serves at http://localhost:3000 (requires NEXT_PUBLIC_API_BASE set)
```

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| CORS error in browser console | `main.py` missing `http://localhost:3000` | Verify CORS origins list in `app/main.py` |
| 401 on all API calls | Cookie not sent | Check `credentials: 'include'` in fetch; SameSite=Lax + cross-origin port OK |
| Backend unreachable | Docker not running | `docker compose up -d` |
| Port 3000 in use | Another process | Kill or use `PORT=3001 pnpm dev` |
| `NEXT_PUBLIC_API_BASE` wrong | Env not loaded | Restart dev server after editing `.env.local` |

---

## Artifacts Produced

- `plan.md` — this file
- `research.md` — Phase 0 decisions (8 topics resolved)
- `data-model.md` — Phase 1 entities + UI state
- `contracts/api-endpoints.md` — 51-endpoint contract (24 HTML + 24 JSON documented + 3 JSON undocumented)
- `contracts/types.ts` — Zod schemas + TS types for all payloads
- `quickstart.md` — this file
