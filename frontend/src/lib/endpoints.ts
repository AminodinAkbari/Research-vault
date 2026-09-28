/**
 * Endpoint path/verb map from specs/001-nextjs-frontend/contracts/api-endpoints.md
 * Frontend uses JSON equivalents where available; HTML endpoints preserved for HTMX UI.
 */

// ============================================================================
// JSON API Endpoints under /api/v1 (used by frontend)
// ============================================================================

export const endpoints = {
  // Auth (A1-A2)
  register: "/api/v1/auth/register",
  login: "/api/v1/auth/login",

  // Projects (A3-A5)
  projects: "/api/v1/projects",
  project: (projectId: string) => `/api/v1/projects/${projectId}`,

  // Notes (A6-A10)
  notes: (projectId: string) => `/api/v1/projects/${projectId}/notes`,
  note: (projectId: string, noteId: string) =>
    `/api/v1/projects/${projectId}/notes/${noteId}`,
  noteTags: (projectId: string, noteId: string) =>
    `/api/v1/projects/${projectId}/notes/${noteId}/tags`,
  noteTag: (projectId: string, noteId: string, tagId: string) =>
    `/api/v1/projects/${projectId}/notes/${noteId}/tags/${tagId}`,

  // Links (A13-A16)
  links: (projectId: string) => `/api/v1/projects/${projectId}/links`,
  link: (projectId: string, linkId: string) =>
    `/api/v1/projects/${projectId}/links/${linkId}`,
  linkTags: (projectId: string, linkId: string) =>
    `/api/v1/projects/${projectId}/links/${linkId}/tags`,
  linkTag: (projectId: string, linkId: string, tagId: string) =>
    `/api/v1/projects/${projectId}/links/${linkId}/tags/${tagId}`,

  // Search (A19-A20)
  webSearch: (projectId: string) => `/api/v1/projects/${projectId}/search`,
  collectedSearch: (projectId: string) =>
    `/api/v1/projects/${projectId}/search-collected`,

  // Tags (A21-A23)
  tags: (projectId: string) => `/api/v1/projects/${projectId}/tags`,
  tag: (projectId: string, tagId: string) =>
    `/api/v1/projects/${projectId}/tags/${tagId}`,

  // Export (A24)
  exportMarkdown: (projectId: string) =>
    `/api/v1/projects/${projectId}/export/markdown`,

  // Highlights (H1-H3)
  highlights: (projectId: string, linkId: string) =>
    `/api/v1/projects/${projectId}/links/${linkId}/highlights`,
  highlight: (projectId: string, linkId: string, highlightId: string) =>
    `/api/v1/projects/${projectId}/links/${linkId}/highlights/${highlightId}`,
} as const;

// ============================================================================
// HTML/HTMX Endpoints (root path — only /logout called directly by frontend)
// ============================================================================

export const htmlEndpoints = {
  logout: "/logout",
} as const;
