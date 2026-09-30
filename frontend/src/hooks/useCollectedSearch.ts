"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { CollectedSearchResult } from "@/lib/types";

const ResultList = CollectedSearchResult.array();

/** Keystroke → request delay (HTMX parity: `keyup changed delay:500ms`). */
export const SEARCH_DEBOUNCE_MS = 500;

export interface UseCollectedSearchResult {
  /** Current input value. */
  query: string;
  setQuery: (value: string) => void;
  /** Run the search now instead of waiting for the debounce. */
  submit: () => void;
  /** The query that produced `results` (empty when nothing is searched). */
  activeQuery: string;
  results: CollectedSearchResult[];
  isLoading: boolean;
  isError: boolean;
}

export function useCollectedSearch(
  projectId: string
): UseCollectedSearchResult {
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");

  // FR-021: fire ~500ms after typing stops; an empty query never requests and
  // clears the results immediately.
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setActiveQuery("");
      return;
    }
    const timer = window.setTimeout(
      () => setActiveQuery(trimmed),
      SEARCH_DEBOUNCE_MS
    );
    return () => window.clearTimeout(timer);
  }, [query]);

  const submit = useCallback(() => {
    setActiveQuery(query.trim());
  }, [query]);

  const searchQuery = useQuery({
    queryKey: ["collected-search", projectId, activeQuery],
    queryFn: () =>
      apiFetch(
        `${endpoints.collectedSearch(projectId)}?q=${encodeURIComponent(
          activeQuery
        )}`,
        ResultList
      ),
    enabled: !!projectId && !!activeQuery,
    staleTime: 30000,
  });

  return {
    query,
    setQuery,
    submit,
    activeQuery,
    results: activeQuery ? searchQuery.data ?? [] : [],
    isLoading: !!activeQuery && searchQuery.isLoading,
    isError: !!activeQuery && searchQuery.isError,
  };
}
