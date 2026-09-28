# Implementation Plan: Next.js Frontend (Minimal App Router + Tailwind)

**Branch**: `001-nextjs-frontend` | **Date**: 2026-09-28 | **Spec**: specs/001-nextjs-frontend/spec.md

**Input**: Feature specification from `/specs/001-nextjs-frontend/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Port the existing HTMX-based Research Vault UI to a Next.js 14+ App Router frontend with Tailwind CSS, preserving all functional behavior and API contracts. The frontend lives in `/frontend`, runs on the host via `npm run dev`, and communicates with the existing Docker-backed FastAPI backend at `http://localhost:8000`. No new backend endpoints are created; the sole backend change is a CORS origin addition in `main.py`. Visual design follows the `design-taste-frontend` skill (calm Linear-style, one accent, restrained motion, dual themes).

## Technical Context

**Language/Version**: TypeScript 5.x, Node.js 20+ (LTS)

**Primary Dependencies**: Next.js 14+ (App Router, RSC), Tailwind CSS 3.4+, React 18+, motion/react (Framer Motion successor), Phosphor Icons (`@phosphor-icons/react`), next/font (Geist + Geist Mono), Zod (schema validation), SWR or TanStack Query (server-state caching), js-cookie (cookie utilities for CSRF if needed), date-fns (date formatting)

**Storage**: None (frontend is stateless; all persistence via backend API). Local UI state only (active tab, form inputs, in-flight flags, theme preference).

**Testing**: Vitest (unit), Playwright (E2E against running backend), React Testing Library (component)

**Target Platform**: Linux/macOS/Windows host (dev server); production build static/SSR deployable anywhere Node runs. Browser: modern evergreen (last 2 versions).

**Project Type**: Web application (frontend-only, consumes existing REST API)

**Performance Goals**: LCP < 2.5s, INP < 200ms, CLS < 0.1 (Core Web Vitals); initial JS bundle < 150 kB gzipped; highlight round-trip < 300 ms locally (SC-005)

**Constraints**: 
- Backend frozen except CORS (C-2, C-3)
- Cookie-only auth, no JS token access (constitution)
- Must exercise all 27 endpoints from spec tables (acceptance)
- No Docker service for frontend; `npm run dev` on host
- Dual themes with WCAG AA contrast
- `prefers-reduced-motion` respected
- One accent, one radius, one icon family (design skill)

**Scale/Scope**: 5 screens, 4 tabs in workspace, ~27 API endpoints, 7 entities consumed, single-user self-hosted

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Readable, Maintainable Code | PASS | Component-driven, shared kit, single-purpose modules |
| II. Preserve Existing Behavior | PASS | Porting existing endpoints; no backend behavior changes |
| III. API Backward Compatibility | PASS | All existing endpoints consumed unchanged; CORS only |
| IV. Automated Testing | PASS | Vitest + Playwright planned; E2E covers all user stories |
| V. Secure Config & Secrets | PASS | No secrets in frontend; API base URL via env; cookie auth only |
| VI. Clear Backend/Frontend Separation | PASS | Frontend in `/frontend`; only integration is REST API + cookie |
| VII. Simple Architecture | PASS | RSC + client islands; no over-abstraction; YAGNI |
| VIII. Document Decisions | PASS | ADR/ARCHITECTURE.md updates in same PR |

All gates pass — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-nextjs-frontend/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── api-endpoints.md # Frontend contract: all endpoints consumed
│   └── types.ts         # Shared TypeScript types for API payloads
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Option 2: Web application (frontend + backend detected)
backend/
├── app/                 # Existing FastAPI backend (unchanged except main.py CORS)
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── templates/       # Existing HTMX UI (coexists, untouched)
├── tests/               # Existing pytest suite (unchanged)
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── main.py
├── requirements.txt
└── ...

frontend/                # NEW — this feature
├── src/
│   ├── app/             # Next.js App Router pages (RSC by default)
│   │   ├── (auth)/      # Route group: login, register
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/ # Route group: protected pages
│   │   │   ├── dashboard/
│   │   │   ├── projects/
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx          # Workspace (tabs)
│   │   │   │       ├── links/
│   │   │   │       │   └── [linkId]/
│   │   │   │       │       └── read/     # Reader page
│   │   │   │       └── layout.tsx        # Shared layout with tabs
│   │   │   └── layout.tsx                # Auth guard, header, sidebar
│   │   ├── layout.tsx    # Root: providers, fonts, theme
│   │   ├── globals.css   # Tailwind + CSS variables
│   │   └── api/          # (Optional) Next.js API routes for proxying if needed
│   ├── components/       # Shared UI kit
│   │   ├── ui/           # Button, Input, Select, Badge, Card, Tab, EmptyState, etc.
│   │   ├── forms/        # Form wrappers with validation
│   │   ├── reader/       # Highlight popup, marks engine, highlights panel
│   │   ├── layout/       # Header, Sidebar, TabBar, ProjectHeader
│   │   └── providers/    # ThemeProvider, AuthProvider (client islands)
│   ├── lib/              # Utilities
│   │   ├── api.ts        # Typed fetch wrapper (credentials: 'include')
│   │   ├── auth.ts       # Auth helpers (redirect, logout)
│   │   ├── types.ts      # Zod schemas + TS types for all API payloads
│   │   ├── utils.ts      # cn(), formatDate(), offset utils
│   │   └── constants.ts  # Colors, radii, breakpoints, endpoints
│   ├── hooks/            # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useProjects.ts
│   │   ├── useNotes.ts
│   │   ├── useLinks.ts
│   │   ├── useTags.ts
│   │   ├── useSearch.ts
│   │   └── useHighlights.ts
│   └── styles/           # (Optional) additional global styles
├── public/               # Static assets (favicon, etc.)
├── tests/
│   ├── e2e/              # Playwright specs
│   ├── unit/             # Vitest specs
│   └── fixtures/         # Test data/fixtures
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── .env.example          # NEXT_PUBLIC_API_BASE=http://localhost:8000
├── .eslintrc.js
├── .prettierrc
└── vitest.config.ts
```

**Structure Decision**: Option 2 (Web application) — the repository already has a `backend/` (`/app`) and this feature adds `frontend/` at the root. The frontend uses Next.js App Router with route groups for auth vs. protected areas, shared component library, typed API layer, and custom hooks for server-state management.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

---

## Phase 0: Research

### Research Tasks

1. **Next.js 14 App Router + RSC patterns for auth-gated apps** — best practices for cookie-based auth with credentialed fetches, route groups, middleware vs. layout guards.
2. **Tailwind CSS v4 vs v3** — project uses Tailwind v3 currently (no v4 migration in backend); confirm v3 is correct for frontend.
3. **SWR vs TanStack Query for credentialed cookie auth** — which handles `credentials: 'include'` + cache invalidation better for this use case.
4. **Motion/react (Framer Motion) integration in RSC** — client island boundaries for highlight popup, mark animations.
5. **Zod + fetch wrapper for typed API layer** — patterns for shared types between request/response, error handling.
6. **Phosphor Icons with Next.js** — tree-shaking, stroke weight consistency.
7. **Playwright + Vitest setup for Next.js** — running against external backend at `localhost:8000`.
8. **Highlight mark engine port** — the existing JS offset/computed-text-node algorithm must be ported faithfully; research if any existing library handles this (likely not; custom port required).

### Research Output

All findings consolidated in `research.md` with Decision / Rationale / Alternatives for each.

---

## Phase 1: Design & Contracts

### 1. Data Model (`data-model.md`)

Extract the 7 frontend-consumed entities from spec §Key Entities, annotate with:
- Field names matching backend JSON schemas (from `app/schemas/`)
- Validation rules (required, min length, enums for status/extraction)
- Relationships (Project 1→N Note, Link, Tag; Link 1→N Highlight; Tag M→N Note/Link)
- Frontend-only UI state (activeTab, isLoading, selectedHighlightColor, etc.)

### 2. Contracts (`contracts/`)

- **`contracts/api-endpoints.md`**: Complete table of all 27 endpoints from spec (24 HTML/HTMX + 3 JSON highlight), with method, path, auth, request/response shapes, error codes, and which UI screen uses each.
- **`contracts/types.ts`**: Zod schemas + exported TypeScript types for every request/response payload consumed by the frontend (Auth, Project, Note, Link, Tag, Highlight, SearchResult, error envelopes).

### 3. Quickstart (`quickstart.md`)

Runnable validation guide:
- Prerequisites: Docker Compose up (backend), Node 20+, pnpm/npm
- Setup: `cd frontend && cp .env.example .env.local && npm install`
- Run: `npm run dev` (frontend at `localhost:3000`) + verify backend at `localhost:8000`
- Test matrix: 7 user stories → Playwright commands + expected outcomes
- Lint/typecheck: `npm run lint && npm run typecheck`
- Unit tests: `npm run test`
- E2E: `npm run test:e2e` (requires running backend)