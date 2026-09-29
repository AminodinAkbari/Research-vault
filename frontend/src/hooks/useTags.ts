import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { TagRead, TagCreate } from "@/lib/types";

const TagList = TagRead.array();
const NoContent = z.undefined();

export interface UseTagsResult {
  tags: TagRead[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  createTag: (data: TagCreate) => Promise<TagRead>;
  isCreating: boolean;
  deleteTag: (tagId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useTags(projectId: string): UseTagsResult {
  const queryClient = useQueryClient();
  const queryKey = ["tags", projectId];
  const invalidateTags = () => queryClient.invalidateQueries({ queryKey });
  // A deleted tag disappears from every note/link that carried it
  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ["notes", projectId] });
    queryClient.invalidateQueries({ queryKey: ["links", projectId] });
  };

  const listQuery = useQuery({
    queryKey,
    queryFn: () => apiFetch(endpoints.tags(projectId), TagList),
    staleTime: 15000,
    enabled: !!projectId,
  });

  const createMutation = useMutation({
    mutationFn: (data: TagCreate) =>
      apiFetch(endpoints.tags(projectId), TagRead, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: invalidateTags,
  });

  const deleteMutation = useMutation({
    mutationFn: (tagId: string) =>
      apiFetch(endpoints.tag(projectId, tagId), NoContent, {
        method: "DELETE",
      }),
    onSuccess: invalidateAll,
  });

  return {
    tags: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    createTag: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    deleteTag: (tagId) => deleteMutation.mutateAsync(tagId),
    isDeleting: deleteMutation.isPending,
  };
}
