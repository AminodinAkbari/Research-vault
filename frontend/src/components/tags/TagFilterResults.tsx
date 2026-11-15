"use client";

import { Button } from "@/components/ui/Button";
import {
  UnifiedResults,
  UnifiedResult,
} from "@/components/search/UnifiedResults";
import { NoteRead, SavedLinkRead } from "@/lib/types";

export interface TagFilterResultsProps {
  projectId: string;
  tag: { id: string; name: string };
  notes: NoteRead[];
  links: SavedLinkRead[];
  isLoading?: boolean;
  onClear: () => void;
  onNoteSelect?: (noteId: string) => void;
}

function noteSnippet(content?: string | null): string | undefined {
  if (!content) return undefined;
  return content.length > 150 ? `${content.slice(0, 150)}…` : content;
}

/**
 * FR-020: unified note/link list for one tag, rendered above the tabs.
 * Derived client-side from the notes and links payloads (spec Assumption —
 * the tag-items endpoint is left to the HTMX UI).
 */
export function TagFilterResults({
  projectId,
  tag,
  notes,
  links,
  isLoading = false,
  onClear,
  onNoteSelect,
}: TagFilterResultsProps) {
  const items: UnifiedResult[] = [
    ...notes
      .filter((note) => note.tags.some((t) => t.id === tag.id))
      .map((note) => ({
        type: "note" as const,
        id: note.id,
        title: note.title,
        snippet: noteSnippet(note.content),
      })),
    ...links
      .filter((link) => link.tags.some((t) => t.id === tag.id))
      .map((link) => ({
        type: "link" as const,
        id: link.id,
        title: link.title,
        snippet: link.snippet || undefined,
      })),
  ];

  return (
    <section
      id="tag-filter-results"
      aria-label={`Items tagged ${tag.name}`}
      className="space-y-3"
    >
      <header className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">
          Items tagged &quot;{tag.name}&quot;
        </h2>
        <Button variant="outline" size="sm" onClick={onClear}>
          Clear filter
        </Button>
      </header>

      <div aria-live="polite">
        {isLoading ? (
          <p aria-busy="true" className="text-sm text-muted-foreground">
            Loading tagged items…
          </p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No items tagged &quot;{tag.name}&quot; yet.
          </p>
        ) : (
          <UnifiedResults
            projectId={projectId}
            results={items}
            onNoteSelect={onNoteSelect}
          />
        )}
      </div>
    </section>
  );
}
