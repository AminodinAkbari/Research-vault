"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";

export interface UnifiedResult {
  type: "note" | "link";
  id: string;
  title: string;
  snippet?: string;
}

export interface UnifiedResultsProps {
  projectId: string;
  results: UnifiedResult[];
  /** Notes jump to the item in the Notes tab; links open the reader. */
  onNoteSelect?: (noteId: string) => void;
}

/**
 * Shared relevance/tag-filter list: type badge, navigable title, snippet.
 */
export function UnifiedResults({
  projectId,
  results,
  onNoteSelect,
}: UnifiedResultsProps) {
  return (
    <ul className="flex list-none flex-col gap-3 p-0 m-0">
      {results.map((result) => {
        const isNote = result.type === "note";
        const href = isNote
          ? `/projects/${projectId}#note-${result.id}`
          : `/projects/${projectId}/links/${result.id}/read`;
        return (
          <li key={`${result.type}-${result.id}`}>
            <article className="rounded-lg border border-border bg-background p-3">
              <header className="flex items-center gap-2">
                <Badge variant={isNote ? "note" : "link"}>
                  {isNote ? "Note" : "Link"}
                </Badge>
                <Link
                  href={href}
                  className="text-sm font-medium text-foreground transition-colors hover:text-accent"
                  onClick={
                    isNote && onNoteSelect
                      ? (event) => {
                          event.preventDefault();
                          onNoteSelect(result.id);
                        }
                      : undefined
                  }
                >
                  {result.title}
                </Link>
              </header>
              {result.snippet && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {result.snippet}
                </p>
              )}
            </article>
          </li>
        );
      })}
    </ul>
  );
}
