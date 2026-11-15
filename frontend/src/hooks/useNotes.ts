import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { NoteRead, NoteCreate, NoteUpdate } from "@/lib/types";

const NoteList = NoteRead.array();
const NoContent = z.undefined();

export interface UseNotesResult {
  notes: NoteRead[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  createNote: (data: NoteCreate) => Promise<NoteRead>;
  isCreating: boolean;
  updateNote: (noteId: string, data: NoteUpdate) => Promise<NoteRead>;
  isUpdating: boolean;
  deleteNote: (noteId: string) => Promise<void>;
  isDeleting: boolean;
  attachTags: (noteId: string, tagIds: string[]) => Promise<NoteRead>;
  detachTag: (noteId: string, tagId: string) => Promise<NoteRead>;
}

export function useNotes(projectId: string): UseNotesResult {
  const queryClient = useQueryClient();
  const queryKey = ["notes", projectId];
  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const listQuery = useQuery({
    queryKey,
    queryFn: () => apiFetch(endpoints.notes(projectId), NoteList),
    staleTime: 15000,
    enabled: !!projectId,
  });

  const createMutation = useMutation({
    mutationFn: (data: NoteCreate) =>
      apiFetch(endpoints.notes(projectId), NoteRead, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: ({ noteId, data }: { noteId: string; data: NoteUpdate }) =>
      apiFetch(endpoints.note(projectId, noteId), NoteRead, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) =>
      apiFetch(endpoints.note(projectId, noteId), NoContent, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });

  const attachMutation = useMutation({
    mutationFn: ({ noteId, tagIds }: { noteId: string; tagIds: string[] }) =>
      apiFetch(endpoints.noteTags(projectId, noteId), NoteRead, {
        method: "POST",
        body: JSON.stringify({ tag_ids: tagIds }),
      }),
    onSuccess: invalidate,
  });

  const detachMutation = useMutation({
    mutationFn: ({ noteId, tagId }: { noteId: string; tagId: string }) =>
      apiFetch(endpoints.noteTag(projectId, noteId, tagId), NoteRead, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });

  return {
    notes: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    createNote: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    updateNote: (noteId, data) => updateMutation.mutateAsync({ noteId, data }),
    isUpdating: updateMutation.isPending,
    deleteNote: (noteId) => deleteMutation.mutateAsync(noteId),
    isDeleting: deleteMutation.isPending,
    attachTags: (noteId, tagIds) =>
      attachMutation.mutateAsync({ noteId, tagIds }),
    detachTag: (noteId, tagId) => detachMutation.mutateAsync({ noteId, tagId }),
  };
}
