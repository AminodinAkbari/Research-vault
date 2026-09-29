import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { SavedLinkRead, SavedLinkCreate } from "@/lib/types";

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
