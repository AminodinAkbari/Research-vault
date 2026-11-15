<!-- Sync Impact Report
- Version change: unratified template scaffold → 1.0.0 (initial ratification)
- Modified principles:
  - [PRINCIPLE_1_NAME] → I. Readable, Maintainable Code (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] → II. Preserve Existing Behavior (NON-NEGOTIABLE)
  - [PRINCIPLE_3_NAME] → III. API Backward Compatibility (NON-NEGOTIABLE)
  - [PRINCIPLE_4_NAME] → IV. Automated Testing of Important Behavior (NON-NEGOTIABLE)
  - [PRINCIPLE_5_NAME] → V. Secure Configuration & Secrets Handling (NON-NEGOTIABLE)
- Added principles:
  - VI. Clear Backend / Frontend Separation
  - VII. Simple Architecture Over Unnecessary Abstractions
  - VIII. Document Significant Architectural Decisions
- Added sections:
  - Development Workflow & Quality Gates
  - Frontend / Backend Boundary
  - Governance (amendment procedure, versioning policy, compliance review)
- Removed sections: none (previous file was an unfilled template; example
  comments embedded in the scaffold were dropped once replaced)
- Follow-up TODOs: none — all placeholders replaced.
- Note: this HTML comment is temporary scratch material for review of the
  amendment and MUST be removed before the constitution is committed.
-->

# Research Vault Constitution

## Core Principles

### I. Readable, Maintainable Code (NON-NEGOTIABLE)

- Code is read far more often than it is written; every change MUST optimize
  for the comprehension of the next reader, not cleverness.
- New code MUST follow the conventions of the module it lives in (naming,
  async patterns, Pydantic schemas, route → service → model layering).
- Every function and module MUST have a single, stateable purpose; if a
  reviewer cannot describe it in one sentence, it MUST be split, renamed, or
  simplified before merge.
- Comments MUST explain *why*, not *what*. Duplication MUST be extracted only
  when two or more real call sites exist today — never speculatively.
- Rationale: this is a solo-maintained portfolio project; code that only its
  author can parse becomes unmaintainable the moment attention moves on.

### II. Preserve Existing Behavior (NON-NEGOTIABLE)

- The existing FastAPI backend — its endpoints, background tasks, and
  service-layer behavior — MUST keep working exactly as documented in
  `API-SPEC.md` and `ARCHITECTURE.md` unless a change is explicitly requested
  through a spec.
- Refactors MUST be behavior-preserving: the full test suite MUST pass before
  and after (`pytest`), proving old behavior still holds.
- Intentional behavior fixes are the only exemption; they MUST be called out
  prominently in the PR description and covered by a test that fails before
  the fix and passes after.
- Existing features that appear superseded (e.g., the HTMX UI during a
  frontend migration) MUST NOT be removed until their replacement ships and
  the removal is agreed in a spec.

### III. API Backward Compatibility (NON-NEGOTIABLE)

- The `/api/v1` contract recorded in `API-SPEC.md` MUST remain backward
  compatible; existing consumers (the HTMX UI, scripts, the future Next.js
  frontend) MUST NOT break.
- Additive changes (new endpoints, new optional request fields, new response
  fields) are the default and MUST be documented in `API-SPEC.md` in the same
  PR that implements them.
- Breaking changes (removing/renaming fields, tightening validation, changing
  status codes or auth semantics) REQUIRE a new version prefix (`/api/v2`),
  a migration note for consumers, and an updated `API-SPEC.md` — all approved
  before implementation.
- Deprecations MUST announce a replacement first and keep the old path
  working until a spec says otherwise.

### IV. Automated Testing of Important Behavior (NON-NEGOTIABLE)

- Every endpoint MUST have tests covering its happy path plus its auth and
  ownership failure modes; the existing suite in `tests/` is the baseline,
  not a target to shrink.
- Any bug fix MUST include a regression test; any new feature or endpoint
  MUST ship with its tests in the same PR.
- Tests MUST be deterministic and self-contained: external services (Redis,
  SearXNG, AI providers, HTTP targets) are faked or stubbed exactly as the
  current suite does — no real network calls.
- The full `pytest` run MUST be green before any merge; test failures block
  merge regardless of how small the change appears.

### V. Secure Configuration & Secrets Handling (NON-NEGOTIABLE)

- Secrets (JWT secret, database credentials, AI provider keys) MUST come
  exclusively from environment variables / `.env`; `.env` MUST stay
  gitignored and `.env.example` MUST document every variable with placeholder
  values only.
- `JWT_SECRET` and any `changeme`-style default MUST be replaced with a long
  random value before any deployment beyond local development.
- Real credentials MUST NEVER appear in code, logs, tests, committed compose
  files, docs, or screenshots.
- AI provider keys remain optional: with no keys configured the backend MUST
  degrade gracefully and stay fully usable, as it does today.
- Rationale: this app is self-hosted and holds personal research data plus
  third-party API keys; a leaked secret is a full compromise.

### VI. Clear Backend / Frontend Separation

- The backend owns data, business rules, authorization, validation,
  persistence, and background work. The frontend owns presentation,
  client-side routing, and transient UI state. Neither may absorb the other's
  responsibilities.
- The versioned JSON REST API (`/api/v1`) is the ONLY integration surface
  between them; the frontend MUST NOT touch the database, Redis, or internal
  services directly.
- Browser-visible configuration is limited to public values (API base URL,
  feature flags); secrets and provider keys MUST never reach frontend code.
- Authorization and authoritative validation are re-checked by the backend on
  every request; frontend checks are a UX convenience only and MUST NOT be
  relied on for security.
- Rationale: a clean contract lets the Next.js frontend evolve (or be
  replaced) without touching backend code, and keeps the API independently
  scriptable.

### VII. Simple Architecture Over Unnecessary Abstractions

- Prefer direct, obvious code (routes → services → models) over layers of
  indirection. No repository, abstract-factory, or strategy patterns unless
  at least two concrete implementations exist today.
- YAGNI: no speculative config options, plugin systems, generic frameworks,
  or "flexible" abstractions before a second real use case exists.
- New dependencies MUST be justified in the PR: what existing code or
  standard library they replace, and why they are worth the maintenance cost.
- Existing infrastructure (FastAPI, SQLAlchemy, Celery, Redis, Alembic) MUST
  be reused before any new infrastructure or framework is introduced.
- Rationale: for a project of this size, an extra abstraction layer costs
  more in reading time than it saves in flexibility.

### VIII. Document Significant Architectural Decisions

- Decisions that are costly to reverse — schema changes, auth model changes,
  API versioning moves, new infrastructure services, frontend framework or
  contract changes — MUST be recorded as an Architecture Decision Record
  (ADR) or a section in `ARCHITECTURE.md` in the same PR that introduces
  them.
- Every such record MUST state: context, options considered, the decision,
  and its consequences.
- `ARCHITECTURE.md`, `API-SPEC.md`, and `UI-SPEC.md` MUST be updated in the
  same PR whenever the behavior they describe changes; docs that lag code are
  treated as a defect.
- Rationale: without a written record, "why is this here?" becomes
  unanswerable and the next contributor re-litigates settled decisions.

## Development Workflow & Quality Gates

- Work happens on feature branches merged via PR; commit messages follow the
  existing Conventional Commits style (`feat:`, `fix:`, `docs:`, `refactor:`).
- Definition of Done for every PR:
  1. Full `pytest` suite green.
  2. New/changed behavior covered by tests (per Principle IV).
  3. `API-SPEC.md` updated if any endpoint changed (per Principle III).
  4. `ARCHITECTURE.md` / ADR updated if an architectural decision changed
     (per Principle VIII).
  5. No secrets or personal data committed (per Principle V).
- Database schema changes MUST ship with an Alembic migration in the same PR
  as the code that depends on it; migrations MUST be reversible (`downgrade`)
  unless a written justification says otherwise.
- Review questions every PR MUST answer: Does it preserve existing behavior?
  Is it the simplest version that works? Is the backend/frontend boundary
  intact?

## Frontend / Backend Boundary

These rules govern the upcoming Next.js frontend (see `UI-SPEC.md`) and keep
it decoupled from the FastAPI backend.

- The frontend lives in its own top-level directory with its own toolchain
  (Node, linting, tests); backend code stays Python-only and MUST NOT import
  or scaffold frontend assets beyond serving them.
- The frontend consumes ONLY the REST API documented in `API-SPEC.md` — never
  server-rendered fragments or undocumented internal endpoints. API responses
  MUST remain framework-agnostic JSON.
- Authentication uses the existing contract: JWT issued by `/api/v1/auth/*`
  delivered as an httpOnly `access_token` cookie. The frontend MUST NOT read
  the token with JavaScript or store it in `localStorage`.
- Business rules (permissions, rate limits, tag limits, status workflows)
  live in the backend; the frontend MUST NOT re-implement them — it displays
  the API's validation and error responses.
- The backend MUST NOT embed frontend-specific concerns: no Next.js-specific
  payloads, no presentation logic in API responses, no coupling to frontend
  routes.
- Changes required by the frontend go through the API first and follow
  Principle III; the frontend never forces a breaking API change.

## Governance

- This constitution supersedes informal practices and conflicting
  conventions. When a PR conflicts with the constitution, either the PR
  changes or this constitution is amended first — silence is not consent.
- **Amendment procedure:** propose the change as a PR to this file with
  rationale and, where behavior changes, a migration plan; amendments require
  explicit approval and a version bump per the policy below.
- **Versioning policy (SemVer for governance):**
  - MAJOR: removing or redefining a principle, or narrowing an existing rule
    in a backward-incompatible way.
  - MINOR: adding a principle or section, or materially expanding guidance.
  - PATCH: clarifications, wording, and typo fixes with no semantic change.
- **Compliance review:** every PR review MUST check compliance with
  Principles I–VIII and the workflow gates above; violations require explicit
  justification and approval in the PR. Unjustified complexity is itself a
  violation (Principle VII).
- Runtime technical guidance lives in `ARCHITECTURE.md`, `API-SPEC.md`, and
  `UI-SPEC.md`; those documents MUST stay consistent with this constitution,
  and in a conflict the constitution prevails until amended.

**Version**: 1.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-09-28
