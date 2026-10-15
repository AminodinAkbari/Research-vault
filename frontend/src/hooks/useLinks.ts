import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import {
  ExplainRequest,
  ExplainResponse,
  HighlightRead,
  SavedLinkRead,
  SavedLinkCreate,
} from "@/lib/types";

const LinkList = SavedLinkRead.array();
const NoContent = z.undefined();

export interface UseLinksResult {
  links: SavedLinkRead[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  createLink: (data: SavedLinkCreate) => Promise<SavedLinkRead>;
  isCreating: boolean;
  deleteLink: (linkId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useLinks(projectId: string): UseLinksResult {
  const queryClient = useQueryClient();
  const queryKey = ["links", projectId];
  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const listQuery = useQuery({
    queryKey,
    queryFn: () => apiFetch(endpoints.links(projectId), LinkList),
    staleTime: 15000,
    enabled: !!projectId,
  });

  const createMutation = useMutation({
    mutationFn: (data: SavedLinkCreate) =>
      apiFetch(endpoints.links(projectId), SavedLinkRead, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (linkId: string) =>
      apiFetch(endpoints.link(projectId, linkId), NoContent, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });

  return {
    links: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    createLink: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    deleteLink: (linkId) => deleteMutation.mutateAsync(linkId),
    isDeleting: deleteMutation.isPending,
  };
}

/**
 * Locate the highlight the explain endpoint just persisted out of the
 * response list. The created item matches the request exactly; when the same
 * text was explained before, prefer the most recently created duplicate
 * (the list is ordered by created_at ascending).
 */
export function pickExplainedHighlight(
  highlights: HighlightRead[],
  request: ExplainRequest
): HighlightRead | undefined {
  const matches = highlights.filter(
    (h) =>
      h.selected_text === request.selected_text &&
      h.start_offset === request.start_offset &&
      h.end_offset === request.end_offset
  );
  if (matches.length === 0) return undefined;
  return matches.reduce((latest, h) =>
    h.created_at.getTime() >= latest.created_at.getTime() ? h : latest
  );
}

export interface UseExplainTextResult {
  explainText: (data: ExplainRequest) => Promise<HighlightRead[]>;
  isExplaining: boolean;
  explainResult: HighlightRead[] | undefined;
  explainError: unknown;
  resetExplain: () => void;
}

/**
 * POST /projects/{project_id}/links/{link_id}/explain — asks the AI to explain
 * the selected text. The backend persists the explanation as a yellow
 * highlight, so the highlights list (and therefore the article marks) is
 * invalidated once the request succeeds.
 */
export function useExplainText(
  projectId: string,
  linkId: string
): UseExplainTextResult {
  const queryClient = useQueryClient();
  const explainMutation = useMutation({
    mutationFn: (data: ExplainRequest) =>
      apiFetch(endpoints.linkExplain(projectId, linkId), ExplainResponse, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["highlights", projectId, linkId],
      }),
  });

  return {
    explainText: explainMutation.mutateAsync,
    isExplaining: explainMutation.isPending,
    explainResult: explainMutation.data,
    explainError: explainMutation.error,
    resetExplain: explainMutation.reset,
  };
}
