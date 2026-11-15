# Research Findings: Next.js Frontend Port

## 1. Next.js 14 App Router + RSC patterns for auth-gated apps

**Decision**: Use route groups with a shared protected layout (`(dashboard)/layout.tsx`) that runs a server-side auth check via `fetch(`${API_BASE}/api/v1/projects`, { credentials: 'include' })`. If 401/redirect, redirect to `/login`. No middleware needed — layout guard is simpler and works with RSC.

**Rationale**: 
- Middleware runs on Edge runtime with limited Node APIs; cookie parsing is awkward.
- Layout guard runs in Node, has full access to `cookies()` (via `next/headers`) and can call backend directly.
- Route groups keep URL structure clean (`/dashboard`, `/projects/[id]`) while sharing auth logic.
- Public routes (`/login`, `/register`) live in separate `(auth)` group without guard.

**Alternatives considered**: 
- Middleware with `next-auth` — overkill, adds dependency, middleware + RSC cookie handling is fragile.
- Client-side `useEffect` auth check — flash of unprotected content, not SSR-friendly.

---

## 2. Tailwind CSS v4 vs v3

**Decision**: Tailwind CSS v3.4+ (stable, current project version).

**Rationale**: 
- The existing backend uses Pico.css via CDN; no Tailwind in backend.
- v4 is still in beta/RC (as of 2026-09), requires PostCSS plugin changes (`@tailwindcss/postcss`), and the design skill references v3 conventions.
- v3.4 has full feature parity needed (CSS variables, container queries, `dark:` variant).
- Zero migration risk; existing Tailwind knowledge applies directly.

**Alternatives considered**: 
- v4 beta — not production-ready for a portfolio project; potential breaking changes.

---

## 3. SWR vs TanStack Query for credentialed cookie auth

**Decision**: TanStack Query (v5) with `credentials: 'include'` on the fetch wrapper.

**Rationale**: 
- TanStack Query v5 has first-class support for `credentials: 'include'` via `fetchOptions`.
- Better mutation API for the many create/edit/delete actions (FR-011, FR-013, FR-014, FR-019, FR-023).
- `queryClient.invalidateQueries()` integrates cleanly with the "update in place" UX (FR-010).
- Devtools excellent for debugging cache state during development.
- SWR's mutation API is lighter but less expressive for optimistic updates + rollback on error.

**Alternatives considered**: 
- SWR — simpler, smaller bundle (~5 kB vs ~13 kB), but mutations are less ergonomic for this many write paths.
- React Query v4 — superseded by v5; no reason to use older major.

---

## 4. Motion/react integration in RSC

**Decision**: All motion components in dedicated `'use client'` islands: `HighlightPopup`, `HighlightMarks`, `TabTransition`, `Toast`. The rest of the app (layouts, lists, forms) stays server-rendered with zero JS.

**Rationale**: 
- Motion requires browser APIs (`useMotionValue`, `useAnimation`, DOM refs) — cannot run in RSC.
- Isolating to leaf components minimizes client bundle and preserves RSC benefits (streaming, SEO, no hydration mismatch).
- Highlight popup + marks engine is the only complex animation; tabs can use simple CSS transitions.

**Alternatives considered**: 
- CSS-only animations — insufficient for highlight popup positioning + mark sync (needs JS for selection offsets).
- Framer Motion (legacy package) — `motion/react` is the current recommended import path.

---

## 5. Zod + fetch wrapper for typed API layer

**Decision**: Central `lib/api.ts` with a typed `apiFetch<T>(path, options?)` returning parsed Zod schema. All endpoints defined in `lib/endpoints.ts` with Zod schemas for request/response. Errors thrown as typed `ApiError` with status + parsed body.

**Rationale**: 
- Single source of truth for API contracts (matches spec §Frontend Contract Compatibility tables).
- Zod validates at runtime — catches backend drift early in dev.
- TypeScript types inferred from Zod (`z.infer<typeof Schema>`) — no duplication.
- `credentials: 'include'` baked into wrapper; no caller opts out.

**Alternatives considered**: 
- Manual TypeScript interfaces — no runtime validation, drift undetected.
- tRPC / OpenAPI codegen — backend is not tRPC; OpenAPI spec incomplete (missing 24 endpoints).

---

## 6. Phosphor Icons with Next.js

**Decision**: `@phosphor-icons/react` (v1.4+), import individual icons (`import { Plus, Trash, Tag, MagnifyingGlass } from '@phosphor-icons/react'`). Configure `strokeWidth: 1.5` globally via a wrapper component `<Icon name="Plus" />`.

**Rationale**: 
- Phosphor is the skill's #1 recommended family; consistent stroke weights, large icon set.
- Tree-shaking works with named imports; bundle impact minimal (~2 kB per icon used).
- Wrapper ensures consistent `size`, `strokeWidth`, `aria-hidden` across app.

**Alternatives considered**: 
- Lucide — explicitly discouraged by skill unless project already uses it.
- Tabler — larger bundle, less distinctive style.
- Hand-rolled SVG — banned by skill.

---

## 7. Playwright + Vitest setup for Next.js

**Decision**: 
- **Vitest**: `vitest.config.ts` with `environment: 'jsdom'`, `setupFiles: ['./tests/setup.ts']`, `include: ['tests/unit/**/*.test.ts']`. React Testing Library for component tests.
- **Playwright**: `playwright.config.ts` with `baseURL: 'http://localhost:3000'`, `webServer: { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI }`, `use: { baseURL: 'http://localhost:3000' }`. Tests target `http://localhost:8000` backend via frontend.

**Rationale**: 
- Vitest is faster than Jest, native ESM, works with Next.js via `next/vitest` or manual config.
- Playwright's `webServer` auto-starts dev server for local runs; CI uses existing server.
- Backend runs separately in Docker; Playwright tests hit frontend which proxies to backend.

**Alternatives considered**: 
- Cypress — heavier, slower, less parallelizable.
- Jest — slower, legacy config pain with Next.js 14.

---

## 8. Highlight mark engine port

**Decision**: Port the existing `links/read.html` inline script algorithm to a React hook `useHighlightMarks(articleRef, highlights)` in `hooks/useHighlights.ts`. The algorithm:
1. Walks text nodes under the article root to build cumulative character offsets.
2. Sorts highlights by `startOffset` descending.
3. For each highlight, finds start/end text nodes via binary search on offsets.
4. Uses `Range.surroundContents()` or manual node splitting to wrap with `<mark>`.
5. Clears all marks on re-apply (`articleRef.current.normalize()` + remove existing marks).
6. Runs on mount + whenever `highlights` array changes (from TanStack Query cache).

**Rationale**: 
- The existing algorithm is battle-tested in production (handles overlapping, adjacent, out-of-order highlights).
- No existing library solves "wrap arbitrary text ranges by global character offset in a dynamic DOM" — this is a niche problem.
- Porting preserves exact behavior (bug-for-bug compatibility with HTMX UI).
- React hook isolates side effects; runs in `useEffect` after render.

**Alternatives considered**: 
- `react-highlight-words` — only works for search-term highlighting, not arbitrary offsets.
- `mark.js` — unmaintained, heavy, doesn't support offset-based API.
- CSS `::highlight` (Highlight API) — not widely supported, no offset mapping.

---

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| Auth guard | Layout server-component check | Simpler than middleware, full Node access |
| Tailwind | v3.4+ | Stable, no migration risk |
| Data fetching | TanStack Query v5 | Best mutation UX, cache invalidation |
| Motion | `motion/react` in client islands | RSC-compatible, minimal client JS |
| API layer | Zod + typed fetch wrapper | Runtime validation, single source of truth |
| Icons | Phosphor (`@phosphor-icons/react`) | Skill #1 choice, tree-shakeable |
| Testing | Vitest + Playwright | Fast unit, reliable E2E vs real backend |
| Highlight engine | Custom port of existing algorithm | Only solution for offset-based marking |

All NEEDS CLARIFICATION items resolved. Proceed to Phase 1.
