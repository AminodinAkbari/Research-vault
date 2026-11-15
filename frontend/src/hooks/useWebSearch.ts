import { useCallback, useState } from "react";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { ApiError, WebSearchResult } from "@/lib/types";

const NETWORK_OR_SEARXNG_COPY = "SearXNG is unavailable.";

export interface UseWebSearchResult {
  results: WebSearchResult[];
  error: string;
  isSearching: boolean;
  hasSearched: boolean;
  search: (query: string) => Promise<void>;
  reset: () => void;
}

export function useWebSearch(projectId: string): UseWebSearchResult {
  const [results, setResults] = useState<WebSearchResult[]>([]);
  const [error, setError] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const search = useCallback(
    async (query: string) => {
      setIsSearching(true);
      setError("");
      setHasSearched(true);
      try {
        const data = await apiFetch(
          endpoints.webSearch(projectId),
          WebSearchResult.array(),
          { method: "POST", body: JSON.stringify({ query }) }
        );
        setResults(data);
        if (data.length === 0) {
          setError("No results found.");
        }
      } catch (err) {
        setResults([]);
        if (err instanceof ApiError && err.status === 401) {
          setError("Session expired — please sign in again");
        } else if (err instanceof ApiError && err.status === 502) {
          setError(NETWORK_OR_SEARXNG_COPY);
        } else if (!(err instanceof ApiError)) {
          // fetch rejection (offline / unreachable service)
          setError(NETWORK_OR_SEARXNG_COPY);
        } else {
          setError("Something went wrong. Please try again.");
        }
      } finally {
        setIsSearching(false);
      }
    },
    [projectId]
  );

  const reset = useCallback(() => {
    setResults([]);
    setError("");
    setHasSearched(false);
  }, []);

  return { results, error, isSearching, hasSearched, search, reset };
}
