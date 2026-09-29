"use client";

import { useState, FormEvent } from "react";
import { useWebSearch } from "@/hooks/useWebSearch";
import { useLinks } from "@/hooks/useLinks";
import { useToast } from "@/components/providers/ToastProvider";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ApiError, WebSearchResult } from "@/lib/types";

export interface WebSearchPanelProps {
  projectId: string;
}

export function WebSearchPanel({ projectId }: WebSearchPanelProps) {
  const { results, error, isSearching, search } = useWebSearch(projectId);
  const { createLink } = useLinks(projectId);
  const { success } = useToast();
  const [query, setQuery] = useState("");
  const [savedUrls, setSavedUrls] = useState<string[]>([]);
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isSearching) return;
    await search(trimmed);
  };

  const handleSave = async (result: WebSearchResult) => {
    setSaveErrors((prev) => ({ ...prev, [result.url]: "" }));
    try {
      await createLink({
        url: result.url,
        title: result.title,
        snippet: result.snippet,
        search_query: query.trim() || null,
      });
      setSavedUrls((prev) =>
        prev.includes(result.url) ? prev : [...prev, result.url]
      );
      success("Saved to your links.");
    } catch (err) {
      let message = "Something went wrong. Please try again.";
      if (err instanceof ApiError && err.status === 401) {
        message = "Session expired — please sign in again";
      } else if (
        err instanceof ApiError &&
        typeof err.body.detail === "string"
      ) {
        message = err.body.detail;
      }
      setSaveErrors((prev) => ({ ...prev, [result.url]: message }));
    }
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        aria-label="Search the web"
        className="flex flex-col gap-4 border border-border rounded-lg p-4"
        noValidate
      >
        <Input
          label="Search the web"
          name="query"
          type="search"
          placeholder="Search the web…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="submit" isLoading={isSearching} className="self-start">
          Search
        </Button>
      </form>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <div aria-live="polite" className="flex flex-col gap-4">
        {results.map((result, index) => {
          const saveError = saveErrors[result.url];
          const isSaved = savedUrls.includes(result.url);
          return (
            <article
              key={`${result.url}-${index}`}
              className="border border-border rounded-lg p-4 bg-background"
            >
              <header className="flex items-center justify-between gap-3">
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-foreground hover:text-accent transition-colors"
                >
                  {result.title}
                </a>
                {result.engine && <Badge>{result.engine}</Badge>}
              </header>

              {result.snippet && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {result.snippet}
                </p>
              )}

              <p className="mt-1 text-xs">
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-all text-accent hover:underline"
                >
                  {result.url}
                </a>
              </p>

              <div className="mt-3">
                {isSaved ? (
                  <Button variant="outline" size="sm" disabled>
                    Saved
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSave(result)}
                  >
                    Save
                  </Button>
                )}
              </div>

              {saveError && (
                <p role="alert" className="mt-2 text-sm text-danger">
                  {saveError}
                </p>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
