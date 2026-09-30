"use client";

import { FormEvent } from "react";
import { useCollectedSearch } from "@/hooks/useCollectedSearch";
import {
  UnifiedResults,
  UnifiedResult,
} from "@/components/search/UnifiedResults";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export interface ProjectSearchBoxProps {
  projectId: string;
  onNoteSelect?: (noteId: string) => void;
}

export function ProjectSearchBox({
  projectId,
  onNoteSelect,
}: ProjectSearchBoxProps) {
  const { query, setQuery, submit, activeQuery, results, isLoading, isError } =
    useCollectedSearch(projectId);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit();
  };

  const unified: UnifiedResult[] = results.map((result) => ({
    type: result.type,
    id: result.id,
    title: result.title,
    snippet: result.snippet,
  }));

  return (
    <section
      aria-label="Search your notes and links"
      className="space-y-3"
    >
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-2 sm:flex-row sm:items-end"
      >
        <div className="flex-1">
          <Input
            label="Search notes & links"
            name="q"
            type="search"
            placeholder="Search notes & links…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <Button type="submit">Search</Button>
      </form>

      {activeQuery && (
        <div id="collected-search-results" aria-live="polite">
          {isLoading ? (
            <p aria-busy="true" className="text-sm text-muted-foreground">
              Searching…
            </p>
          ) : isError ? (
            <p role="alert" className="text-sm text-danger">
              Something went wrong. Please try again.
            </p>
          ) : results.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No matches found for &quot;{activeQuery}&quot;.
            </p>
          ) : (
            <UnifiedResults
              projectId={projectId}
              results={unified}
              onNoteSelect={onNoteSelect}
            />
          )}
        </div>
      )}
    </section>
  );
}
