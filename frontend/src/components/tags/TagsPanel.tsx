"use client";

import { useState, FormEvent } from "react";
import { useTags } from "@/hooks/useTags";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError, TagRead } from "@/lib/types";

export interface TagsPanelProps {
  projectId: string;
  onTagClick?: (tag: { id: string; name: string }) => void;
}

export function TagsPanel({ projectId, onTagClick }: TagsPanelProps) {
  const { tags, isLoading, createTag, isCreating, deleteTag, isDeleting } =
    useTags(projectId);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [pendingDelete, setPendingDelete] = useState<TagRead | null>(null);
  const [deleteError, setDeleteError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    const trimmed = name.trim();
    if (!trimmed) {
      setError("Tag name is required.");
      return;
    }
    if (trimmed.length > 50) {
      setError("Tag name must be 50 characters or less.");
      return;
    }

    try {
      await createTag({ name: trimmed });
      setName("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(`A tag named "${trimmed}" already exists in this project.`);
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else if (
        err instanceof ApiError &&
        typeof err.body.detail === "string"
      ) {
        setError(err.body.detail);
      } else {
        setError("Something went wrong. Please try again.");
      }
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setDeleteError("");
    try {
      await deleteTag(pendingDelete.id);
      setPendingDelete(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setDeleteError("Session expired — please sign in again");
      } else {
        setDeleteError("Something went wrong. Please try again.");
      }
    }
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        aria-label="Create a new tag"
        className="flex flex-col gap-4 border border-border rounded-lg p-4"
        noValidate
      >
        <Input
          label="Tag name"
          name="name"
          required
          maxLength={50}
          placeholder="Tag name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" isLoading={isCreating} className="self-start">
          Add tag
        </Button>
      </form>

      <div aria-live="polite">
        {isLoading ? (
          <p aria-busy="true" className="text-muted-foreground">
            Loading tags…
          </p>
        ) : tags.length === 0 ? (
          <EmptyState title="No tags yet" description="Create one above." />
        ) : (
          <ul className="flex flex-col gap-2 list-none p-0 m-0">
            {tags.map((tag) => (
              <li
                key={tag.id}
                id={`tag-${tag.id}`}
                className="flex items-center justify-between gap-3 border border-border rounded-lg px-4 py-2"
              >
                {onTagClick ? (
                  <button
                    type="button"
                    onClick={() => onTagClick({ id: tag.id, name: tag.name })}
                    className="rounded text-sm font-medium text-foreground transition-colors hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {tag.name}
                  </button>
                ) : (
                  <span className="text-sm font-medium text-foreground">
                    {tag.name}
                  </span>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPendingDelete(tag)}
                >
                  Delete
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete tag"
        message={`Delete tag "${pendingDelete?.name ?? ""}"? It will be removed from all notes.`}
        confirmLabel="Delete"
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => {
          setPendingDelete(null);
          setDeleteError("");
        }}
      />

      {deleteError && (
        <p role="alert" className="text-sm text-danger">
          {deleteError}
        </p>
      )}
    </div>
  );
}
