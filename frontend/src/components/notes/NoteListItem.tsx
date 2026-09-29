"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { NoteEditForm } from "./NoteEditForm";
import { TagAttachPicker } from "./TagAttachPicker";
import { ApiError, NoteRead, NoteUpdate, SavedLinkRead, TagRead } from "@/lib/types";

export interface NoteListItemProps {
  projectId: string;
  note: NoteRead;
  links: SavedLinkRead[];
  tags: TagRead[];
  onSave: (data: NoteUpdate) => Promise<unknown>;
  onDelete: () => Promise<unknown>;
  onAttachTag: (tagId: string) => Promise<unknown>;
  onDetachTag: (tagId: string) => Promise<unknown>;
}

function contentPreview(content: string) {
  if (!content) return null;
  return content.length > 200 ? `${content.slice(0, 200)}…` : content;
}

export function NoteListItem({
  projectId,
  note,
  links,
  tags,
  onSave,
  onDelete,
  onAttachTag,
  onDetachTag,
}: NoteListItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState("");

  const sourceLink = note.source_link_id
    ? links.find((link) => link.id === note.source_link_id)
    : undefined;
  const preview = contentPreview(note.content);

  const handleSave = async (data: NoteUpdate) => {
    setIsSaving(true);
    try {
      await onSave(data);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setError("");
    setIsDeleting(true);
    try {
      await onDelete();
      setShowConfirm(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDetach = async (tagId: string) => {
    setError("");
    try {
      await onDetachTag(tagId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else {
        setError("Something went wrong. Please try again.");
      }
    }
  };

  return (
    <article
      id={`note-${note.id}`}
      className="border border-border rounded-lg p-4 bg-background"
    >
      {isEditing ? (
        <NoteEditForm
          note={note}
          links={links}
          onSave={handleSave}
          onCancel={() => setIsEditing(false)}
          isSaving={isSaving}
        />
      ) : (
        <>
          <header>
            <h3 className="font-semibold text-foreground">{note.title}</h3>
          </header>

          <p className="mt-1 text-sm text-muted-foreground">
            {preview ?? <span className="text-muted-foreground">(No content)</span>}
          </p>

          {sourceLink && (
            <p className="mt-1 text-sm text-muted-foreground">
              Source:{" "}
              <Link
                href={`/projects/${projectId}/links/${sourceLink.id}/read`}
                className="text-accent hover:underline"
              >
                {sourceLink.title}
              </Link>
            </p>
          )}

          <div
            aria-label="Tags on this note"
            className="mt-2 flex flex-wrap items-center gap-2"
          >
            {note.tags.length === 0 ? (
              <span className="text-sm text-muted-foreground">No tags</span>
            ) : (
              note.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center gap-1 rounded-pill bg-muted px-2 py-0.5 text-xs font-medium text-foreground border border-border"
                >
                  {tag.name}
                  <button
                    type="button"
                    onClick={() => handleDetach(tag.id)}
                    title={`Remove tag "${tag.name}"`}
                    aria-label={`Remove tag "${tag.name}"`}
                    className="ml-0.5 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                  >
                    ×
                  </button>
                </span>
              ))
            )}
          </div>

          <div className="mt-3 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPicker((open) => !open)}
              aria-expanded={showPicker}
            >
              Attach tag
            </Button>
            <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
              Edit
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowConfirm(true)}>
              Delete
            </Button>
          </div>

          {showPicker && (
            <TagAttachPicker
              tags={tags}
              attachedTagIds={note.tags.map((tag) => tag.id)}
              onAttach={async (tagId) => {
                await onAttachTag(tagId);
              }}
            />
          )}

          {error && (
            <p role="alert" className="mt-2 text-sm text-danger">
              {error}
            </p>
          )}

          <ConfirmDialog
            open={showConfirm}
            title="Delete note"
            message="Delete this note? This cannot be undone."
            confirmLabel="Delete"
            isLoading={isDeleting}
            onConfirm={handleDelete}
            onCancel={() => setShowConfirm(false)}
          />
        </>
      )}
    </article>
  );
}
