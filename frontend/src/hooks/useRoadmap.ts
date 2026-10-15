import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { RoadmapRequest, RoadmapResponse, RoadmapStep } from "@/lib/types";

export interface UseRoadmapResult {
  roadmap: RoadmapStep[];
  generateRoadmap: (data: RoadmapRequest) => Promise<RoadmapResponse>;
  isGenerating: boolean;
  isError: boolean;
  error: unknown;
  reset: () => void;
}

/**
 * POST /api/v1/roadmap — generate (or fetch cached) AI research roadmap
 * for a subject. The backend only exposes POST, so this is a mutation;
 * the last successful result is kept in `roadmap` until `reset()` is called.
 */
export function useRoadmap(): UseRoadmapResult {
  const generateMutation = useMutation({
    mutationFn: (data: RoadmapRequest) =>
      apiFetch(endpoints.roadmap, RoadmapResponse, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    retry: false, // 502/422 from the AI service should surface immediately
  });

  return {
    roadmap: generateMutation.data?.roadmap ?? [],
    generateRoadmap: generateMutation.mutateAsync,
    isGenerating: generateMutation.isPending,
    isError: generateMutation.isError,
    error: generateMutation.error,
    reset: generateMutation.reset,
  };
}
