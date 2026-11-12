"use client";

import { FormEvent } from "react";
import { Sparkle } from "@phosphor-icons/react";
import { useCollectedSearch } from "@/hooks/useCollectedSearch";
import {
  UnifiedResults,
  UnifiedResult,
} from "@/components/search/UnifiedResults";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { ApiError } from "@/lib/types";

export interface ProjectSearchBoxProps {
  projectId: string;
  onNoteSelect?: (noteId: string) => void;
}

function rerankErrorMessage(error: ApiError): string {
  if (error.status === 429) return "Rate limit reached. Please try again later.";
  if (error.status === 401) return "Authentication required to use AI reranking.";
  return typeof error.body.detail === "string"
    ? error.body.detail
    : "AI reranking failed. Please try again.";
}

export function ProjectSearchBox({
  projectId,
  onNoteSelect,
}: ProjectSearchBoxProps) {
  const {
    query,
    setQuery,
    submit,
    activeQuery,
    results,
    isLoading,
    isError,
    rerank,
    isReranking,
    isReranked,
    rerankError,
  } = useCollectedSearch(projectId);

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
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  leftIcon={<Sparkle size={14} weight="duotone" />}
                  onClick={rerank}
                  isLoading={isReranking}
                  disabled={isReranking}
                >
                  Rerank with AI
                </Button>
                {isReranked && (
                  <Badge variant="success">AI reranked</Badge>
                )}
              </div>

              {rerankError && (
                <p role="alert" className="text-sm text-danger">
                  {rerankErrorMessage(rerankError)}
                </p>
              )}

              <UnifiedResults
                projectId={projectId}
                results={unified}
                onNoteSelect={onNoteSelect}
              />
            </div>
          )}
        </div>
      )}
    </section>
  );
}

