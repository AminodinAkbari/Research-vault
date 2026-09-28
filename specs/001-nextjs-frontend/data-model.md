# Data Model: Next.js Frontend Port

## Entities (Frontend-Consumed)

All entities mirror backend JSON schemas from `app/schemas/`. Types are defined in `contracts/types.ts` with Zod schemas.

---

### 1. Session (Auth Context)

**Backend**: No dedicated schema; carried by `access_token` httpOnly cookie.

**Frontend Type**:
```ts
interface Session {
  isAuthenticated: boolean;
  user?: { id: string; email: string }; // from /api/v1/auth/me if added later
}
```
- **Source**: Cookie presence + 401/200 on authenticated fetch.
- **Lifecycle**: Created by login/register (cookie set by backend); destroyed by logout (POST /logout clears cookie).
- **Frontend-only state**: `isLoading` (initial auth check), `error` (network failure).

---

### 2. Project

**Backend schema**: `app/schemas/project.py` → `ProjectRead`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `id` | `string` (UUID) | Yes | — |
| `user_id` | `string` (UUID) | Yes | — |
| `name` | `string` | Yes | 1–200 chars, not blank |
| `description` | `string \| null` | No | Optional, max 2000 chars |
| `created_at` | `string` (ISO 8601) | Yes | — |

**Relationships**: 
- Owned by one User (via `user_id`)
- 1 → N Notes, Links, Tags

**Frontend-only UI state**: `isSelected`, `isCreating`, `createFormError`

---

### 3. Note

**Backend schema**: `app/schemas/note.py` → `NoteRead`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `id` | `string` (UUID) | Yes | — |
| `project_id` | `string` (UUID) | Yes | — |
| `title` | `string` | Yes | 1–200 chars, not blank |
| `content` | `string` | No | Optional, max 100k chars |
| `source_link_id` | `string` (UUID) \| null | No | Must reference existing Link in same project |
| `created_at` | `string` (ISO 8601) | Yes | — |
| `updated_at` | `string` (ISO 8601) | Yes | — |
| `tags` | `TagResponse[]` | Yes | Array of attached tags |

**Relationships**: 
- Belongs to Project
- Optional reference to SavedLink (source_link)
- M → N Tags

**Frontend-only UI state**: `isEditing`, `editFormData`, `isDeleting`, `showTagPicker`

---

### 4. SavedLink

**Backend schema**: `app/schemas/link.py` → `SavedLinkRead`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `id` | `string` (UUID) | Yes | — |
| `project_id` | `string` (UUID) | Yes | — |
| `url` | `string` (URL) | Yes | Valid URL, max 2048 chars |
| `title` | `string` | Yes | 1–500 chars |
| `snippet` | `string` | No | Optional, max 2000 chars |
| `search_query` | `string \| null` | No | Original search term |
| `extracted_content` | `string \| null` | No | Full article text (set after extraction) |
| `extraction_status` | `enum` | Yes | `pending` \| `completed` \| `failed` |
| `status` | `enum` | Yes | `to_read` \| `reading` \| `done` \| `archived` (reading-list) |
| `created_at` | `string` (ISO 8601) | Yes | — |
| `tags` | `TagResponse[]` | Yes | Array of attached tags |
| `summary` | `string \| null` | No | AI-generated (out of scope for port) |

**Relationships**: 
- Belongs to Project
- 1 → N Highlights
- M → N Tags

**Frontend-only UI state**: `isExtracting`, `showContent` (inline view toggle — out of scope), `extractError`

---

### 5. Tag

**Backend schema**: `app/schemas/tag.py` → `TagRead`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `id` | `string` (UUID) | Yes | — |
| `project_id` | `string` (UUID) | Yes | — |
| `name` | `string` | Yes | 1–50 chars, unique per project, not blank |
| `created_at` | `string` (ISO 8601) | Yes | — |

**Relationships**: 
- Belongs to Project
- M → N Notes, Links (via join tables)

**Frontend-only UI state**: `isCreating`, `createError`, `isDeleting`

---

### 6. Highlight

**Backend schema**: `app/schemas/highlights.py` → `HighlightRead`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `id` | `string` (UUID) | Yes | — |
| `link_id` | `string` (UUID) | Yes | — |
| `selected_text` | `string` | Yes | Not blank, max 5000 chars |
| `annotation` | `string \| null` | No | Optional, max 2000 chars |
| `start_offset` | `integer` | Yes | >= 0, < end_offset |
| `end_offset` | `integer` | Yes | > start_offset, <= article length |
| `color` | `string \| null` | No | One of: `yellow`, `blue`, `green`, `orange`, `purple`, `grey` or hex |
| `created_at` | `string` (ISO 8601) | Yes | — |

**Relationships**: 
- Belongs to SavedLink (via `link_id`)

**Frontend-only UI state**: `isCreating` (popup open), `selectedColor`, `tempMark` (instant visual feedback)

---

### 7. SearchResult

**Backend schemas**: 
- Full-text: `app/schemas/collected_search.py` → `CollectedSearchResult`
- Web: `app/schemas/search.py` → `SearchResult`

**Full-text (project search)**:
```ts
interface CollectedSearchResult {
  type: 'note' | 'link';
  id: string;           // UUID
  title: string;
  snippet: string;
  rank: number;         // relevance score
}
```

**Web (SearXNG)**:
```ts
interface WebSearchResult {
  title: string;
  url: string;
  snippet: string;
  engine: string;
}
```

**Relationships**: 
- Full-text: references Note or Link in current project
- Web: external results; can be saved → becomes SavedLink

**Frontend-only UI state**: `query`, `debouncedQuery`, `isSearching`, `results`, `error`

---

## Frontend-Only UI State (Not Persisted)

| State | Scope | Purpose |
|-------|-------|---------|
| `activeTab` | Workspace | Current tab: 'notes' \| 'links' \| 'websearch' \| 'tags' |
| `theme` | Global | 'light' \| 'dark' \| 'system' (persisted in localStorage) |
| `toasts` | Global | Transient success/error messages (auto-dismiss) |
| `isSidebarOpen` | Mobile | Responsive nav collapse |
| `highlightPopup` | Reader | { range, rect, text } for pending highlight |
| `confirmDialog` | Global | { message, onConfirm } for delete actions |

---

## Validation Rules (Frontend Mirrors)

| Entity | Rule | Frontend Enforcement |
|--------|------|---------------------|
| Project.name | Required, 1–200 chars | Zod + HTML required + maxLength |
| Note.title | Required, 1–200 chars | Zod + HTML required |
| Note.content | Max 100k chars | Zod + textarea maxLength |
| Tag.name | Required, 1–50 chars, unique/project | Zod + server conflict (409) shown inline |
| Highlight.selected_text | Required, not blank | Zod + trim check before submit |
| Highlight.color | Enum of 6 named colors + hex | Radio group / swatch picker |
| Search query | Min 1 char for submit | Debounce 500ms, no request if empty |

---

## State Transitions (Frontend-Driven)

```
Project:  [empty] → create → [list] → select → [workspace]
Note:     [list] → create → [list] → edit → [list] → delete → [list]
          [list] → attach/detach tag → [list]
Link:     [websearch] → save → [list] → extract (pending→completed) → [list]
          [list] → open reader → [reader]
Reader:   [pending/failed] → "Content not yet extracted"
          [completed] → select text → popup → save highlight → [marks applied]
          [highlights] → remove → [marks cleared]
Tag:      [list] → create → [list] → delete → [list]
          [any badge] → click → [filter results] → clear → [workspace]
Search:   [input] → debounce → [results] → clear → []
Auth:     [unauth] → login/register → [dashboard] → logout → [login]
```
