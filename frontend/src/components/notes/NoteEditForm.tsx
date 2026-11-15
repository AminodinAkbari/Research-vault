"use client";

import { useState, FormEvent } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ApiError, NoteRead, NoteUpdate, SavedLinkRead } from "@/lib/types";

export interface NoteEditFormProps {
  note: NoteRead;
  links: SavedLinkRead[];
  onSave: (data: NoteUpdate) => Promise<unknown>;
  onCancel: () => void;
  isSaving?: boolean;
}

export function NoteEditForm({
  note,
  links,
  onSave,
  onCancel,
  isSaving = false,
}: NoteEditFormProps) {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);
  // No stale selection: only preselect when the source link still exists
  const [sourceLinkId, setSourceLinkId] = useState(() =>
    note.source_link_id && links.some((link) => link.id === note.source_link_id)
      ? note.source_link_id
      : ""
  );
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Note title is required.");
      return;
    }
    if (title.length > 200) {
      setError("Note title must be 200 characters or less.");
      return;
    }

    try {
      await onSave({
        title: title.trim(),
        content,
        source_link_id: sourceLinkId || null,
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else if (err instanceof ApiError && typeof err.body.detail === "string") {
        setError(err.body.detail);
      } else {
        setError("Something went wrong. Please try again.");
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Edit note"
      className="flex flex-col gap-4 border border-border rounded-lg p-4 bg-muted/40"
      noValidate
    >
      <Input
        label="Title"
        name="title"
        required
        maxLength={200}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <div className="flex flex-col gap-2">
        <label
          htmlFor={`edit-content-${note.id}`}
          className="text-sm font-medium text-foreground"
        >
          Content
        </label>
        <textarea
          id={`edit-content-${note.id}`}
          name="content"
          rows={4}
          maxLength={100000}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="rounded border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label
          htmlFor={`edit-source-${note.id}`}
          className="text-sm font-medium text-foreground"
        >
          Source link (optional)
        </label>
        <select
          id={`edit-source-${note.id}`}
          name="source_link_id"
          value={sourceLinkId}
          onChange={(e) => setSourceLinkId(e.target.value)}
          className="h-10 w-full rounded border border-input bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <option value="">No source link</option>
          {links.map((link) => (
            <option key={link.id} value={link.id}>
              {link.title}
            </option>
          ))}
        </select>
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex gap-3">
        <Button type="submit" isLoading={isSaving}>
          Save
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSaving}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
