"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { NoteRead, NoteCreate, NoteUpdate, SavedLinkRead } from "@/lib/types";
import { useNotes } from "@/hooks/useNotes";
import { useTags } from "@/hooks/useTags";
import { NoteCreateForm } from "./NoteCreateForm";
import { NoteListItem } from "./NoteListItem";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

export interface NotesPanelProps {
  projectId: string;
  onTagClick?: (tag: { id: string; name: string }) => void;
}

export function NotesPanel({ projectId, onTagClick }: NotesPanelProps) {
  const {
    notes,
    isLoading,
    isError,
    createNote,
    isCreating,
    updateNote,
    deleteNote,
    attachTags,
    detachTag,
  } = useNotes(projectId);
  const { tags } = useTags(projectId);

  const linksQuery = useQuery({
    queryKey: ["links", projectId],
    queryFn: () =>
      apiFetch(endpoints.links(projectId), SavedLinkRead.array()),
    staleTime: 30000,
    enabled: !!projectId,
  });
  const links = linksQuery.data ?? [];

  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-danger">Failed to load notes.</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => window.location.reload()}
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <NoteCreateForm
        links={links}
        onCreate={(data: NoteCreate) => createNote(data)}
        isCreating={isCreating}
      />

      <div aria-live="polite">
        {isLoading ? (
          <p aria-busy="true" className="text-muted-foreground">
            Loading notes…
          </p>
        ) : notes.length === 0 ? (
          <EmptyState
            title="No notes yet"
            description="Add your first note above."
          />
        ) : (
          <ul className="flex flex-col gap-4 list-none p-0 m-0">
            {notes.map((note: NoteRead) => (
              <li key={note.id}>
                <NoteListItem
                  projectId={projectId}
                  note={note}
                  links={links}
                  tags={tags}
                  onSave={(data: NoteUpdate) => updateNote(note.id, data)}
                  onDelete={() => deleteNote(note.id)}
                  onAttachTag={(tagId: string) => attachTags(note.id, [tagId])}
                  onDetachTag={(tagId: string) => detachTag(note.id, tagId)}
                  onTagClick={onTagClick}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
