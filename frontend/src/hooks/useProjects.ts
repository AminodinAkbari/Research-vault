import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { ProjectRead, ProjectCreate } from "@/lib/types";

export function useProjects() {
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiFetch(endpoints.projects, ProjectRead.array()),
    staleTime: 30000,
  });

  const createMutation = useMutation({
    mutationFn: (data: ProjectCreate) =>
      apiFetch(endpoints.projects, ProjectRead, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  return {
    projects: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    createProject: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
  };
}