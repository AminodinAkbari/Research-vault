/**
 * Zod schemas + TypeScript types for all API payloads consumed by the Next.js frontend.
 * Source of truth: app/schemas/*.py + spec §Frontend Contract Compatibility.
 * Runtime validation: Zod schemas used in lib/api.ts fetch wrapper.
 */

import { z } from 'zod';

// ============================================================================
// Enums
// ============================================================================

export const ExtractionStatus = z.enum(['pending', 'completed', 'failed']);
export type ExtractionStatus = z.infer<typeof ExtractionStatus>;

export const ReadingStatus = z.enum(['to_read', 'reading', 'done', 'archived']);
export type ReadingStatus = z.infer<typeof ReadingStatus>;

export const HighlightColor = z.enum(['yellow', 'blue', 'green', 'orange', 'purple', 'grey']);
export type HighlightColor = z.infer<typeof HighlightColor>;

// ============================================================================
// Auth
// ============================================================================

export const RegisterRequest = z.object({
  email: z.string().email().max(320),
  password: z.string().min(8).max(128),
});
export type RegisterRequest = z.infer<typeof RegisterRequest>;

export const RegisterResponse = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  created_at: z.string().datetime(),
  access_token: z.string(),
  token_type: z.literal('bearer'),
});
export type RegisterResponse = z.infer<typeof RegisterResponse>;

export const LoginRequest = z.object({
  email: z.string().email().max(320),
  password: z.string().min(1).max(128),
});
export type LoginRequest = z.infer<typeof LoginRequest>;

export const LoginResponse = z.object({
  access_token: z.string(),
  token_type: z.literal('bearer'),
});
export type LoginResponse = z.infer<typeof LoginResponse>;

// ============================================================================
// Project
// ============================================================================

export const ProjectRead = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  name: z.string().min(1).max(200),
  description: z.string().max(2000).nullable().default(null),
  created_at: z.string().datetime(),
});
export type ProjectRead = z.infer<typeof ProjectRead>;

export const ProjectCreate = z.object({
  name: z.string().min(1).max(200),
  description: z.string().max(2000).optional(),
});
export type ProjectCreate = z.infer<typeof ProjectCreate>;

// ============================================================================
// Tag
// ============================================================================

export const TagRead = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  name: z.string().min(1).max(50),
  created_at: z.string().datetime(),
});
export type TagRead = z.infer<typeof TagRead>;

export const TagCreate = z.object({
  name: z.string().min(1).max(50),
});
export type TagCreate = z.infer<typeof TagCreate>;

export const TagResponse = TagRead; // embedded in Note/Link
export type TagResponse = z.infer<typeof TagResponse>;

// ============================================================================
// Note
// ============================================================================

export const NoteRead = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  title: z.string().min(1).max(200),
  content: z.string().max(100000).default(''),
  source_link_id: z.string().uuid().nullable().default(null),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  tags: z.array(TagResponse).default([]),
});
export type NoteRead = z.infer<typeof NoteRead>;

export const NoteCreate = z.object({
  title: z.string().min(1).max(200),
  content: z.string().max(100000).optional(),
  source_link_id: z.string().uuid().nullable().optional(),
  tag_ids: z.array(z.string().uuid()).optional(),
});
export type NoteCreate = z.infer<typeof NoteCreate>;

export const NoteUpdate = z.object({
  title: z.string().min(1).max(200).optional(),
  content: z.string().max(100000).optional(),
  source_link_id: z.string().uuid().nullable().optional(),
  tag_ids: z.array(z.string().uuid()).optional(),
});
export type NoteUpdate = z.infer<typeof NoteUpdate>;

// ============================================================================
// SavedLink
// ============================================================================

export const SavedLinkRead = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  url: z.string().url().max(2048),
  title: z.string().min(1).max(500),
  snippet: z.string().max(2000).default(''),
  search_query: z.string().nullable().default(null),
  extracted_content: z.string().nullable().default(null),
  extraction_status: ExtractionStatus,
  status: ReadingStatus.default('to_read'),
  created_at: z.string().datetime(),
  tags: z.array(TagResponse).default([]),
  summary: z.string().nullable().default(null),
});
export type SavedLinkRead = z.infer<typeof SavedLinkRead>;

export const SavedLinkCreate = z.object({
  url: z.string().url().max(2048),
  title: z.string().min(1).max(500),
  snippet: z.string().max(2000).optional(),
  search_query: z.string().nullable().optional(),
  tag_ids: z.array(z.string().uuid()).optional(),
});
export type SavedLinkCreate = z.infer<typeof SavedLinkCreate>;

// ============================================================================
// Highlight
// ============================================================================

export const HighlightRead = z.object({
  id: z.string().uuid(),
  link_id: z.string().uuid(),
  selected_text: z.string().min(1).max(5000),
  annotation: z.string().max(2000).nullable().default(null),
  start_offset: z.number().int().min(0),
  end_offset: z.number().int().min(1),
  color: z.string().nullable().default(null), // named color or hex
  created_at: z.string().datetime(),
});
export type HighlightRead = z.infer<typeof HighlightRead>;

export const HighlightCreate = z.object({
  selected_text: z.string().min(1).max(5000),
  annotation: z.string().max(2000).nullable().optional(),
  start_offset: z.number().int().min(0),
  end_offset: z.number().int().min(1),
  color: z.string().nullable().optional(),
});
export type HighlightCreate = z.infer<typeof HighlightCreate>;

// ============================================================================
// Search Results
// ============================================================================

export const CollectedSearchResult = z.object({
  type: z.enum(['note', 'link']),
  id: z.string().uuid(),
  title: z.string(),
  snippet: z.string(),
  rank: z.number(),
});
export type CollectedSearchResult = z.infer<typeof CollectedSearchResult>;

export const WebSearchResult = z.object({
  title: z.string(),
  url: z.string().url(),
  snippet: z.string().default(''),
  engine: z.string().default(''),
});
export type WebSearchResult = z.infer<typeof WebSearchResult>;

// ============================================================================
// Error Envelope
// ============================================================================

export const ApiErrorBody = z.object({
  detail: z.union([z.string(), z.array(z.object({ msg: z.string(), loc: z.array(z.union([z.string(), z.number()])) }))]),
});
export type ApiErrorBody = z.infer<typeof ApiErrorBody>;

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ApiErrorBody,
  ) {
    super(typeof body.detail === 'string' ? body.detail : 'Validation error');
  }
}
