"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { HighlightRead, HighlightCreate } from "@/lib/types";

const HighlightList = HighlightRead.array();
const NoContent = z.undefined();

/**
 * Contract H2 payload with the cross-field rules from the spec:
 * selected_text must not be blank, end_offset must be greater than start_offset.
 */
export const HighlightCreateInput = HighlightCreate.superRefine((value, ctx) => {
  if (!value.selected_text.trim()) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["selected_text"],
      message: "selected_text must not be empty",
    });
  }
  if (value.end_offset <= value.start_offset) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["end_offset"],
      message: "end_offset must be greater than start_offset",
    });
  }
});
export type HighlightCreateInput = z.infer<typeof HighlightCreateInput>;

export interface UseHighlightsResult {
  highlights: HighlightRead[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  createHighlight: (data: HighlightCreateInput) => Promise<HighlightRead>;
  isCreating: boolean;
  deleteHighlight: (highlightId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useHighlights(
  projectId: string,
  linkId: string
): UseHighlightsResult {
  const queryClient = useQueryClient();
  const queryKey = ["highlights", projectId, linkId];
  const invalidate = () => queryClient.invalidateQueries({ queryKey });
  const enabled = !!projectId && !!linkId;

  const listQuery = useQuery({
    queryKey,
    queryFn: () => apiFetch(endpoints.highlights(projectId, linkId), HighlightList),
    staleTime: 10000,
    enabled,
  });

  const createMutation = useMutation({
    mutationFn: (data: HighlightCreateInput) => {
      const parsed = HighlightCreateInput.safeParse(data);
      if (!parsed.success) {
        return Promise.reject(
          new Error(
            parsed.error.issues[0]?.message ?? "Invalid highlight payload"
          )
        );
      }
      return apiFetch(endpoints.highlights(projectId, linkId), HighlightRead, {
        method: "POST",
        body: JSON.stringify(parsed.data),
      });
    },
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (highlightId: string) =>
      apiFetch(endpoints.highlight(projectId, linkId, highlightId), NoContent, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });

  return {
    highlights: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    createHighlight: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    deleteHighlight: (highlightId) => deleteMutation.mutateAsync(highlightId),
    isDeleting: deleteMutation.isPending,
  };
}
