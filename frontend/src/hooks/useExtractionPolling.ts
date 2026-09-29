import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { SavedLinkRead } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

/**
 * FR-016: while any link's extraction is pending, refresh the links list
 * automatically so its status badge turns "Completed" without user action.
 */
export function useExtractionPolling(
  projectId: string,
  links: SavedLinkRead[]
): void {
  const queryClient = useQueryClient();
  const hasPending = links.some(
    (link) => link.extraction_status === "pending"
  );

  useEffect(() => {
    if (!hasPending || !projectId) return;

    const timer = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["links", projectId] });
    }, POLL_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [hasPending, projectId, queryClient]);
}
