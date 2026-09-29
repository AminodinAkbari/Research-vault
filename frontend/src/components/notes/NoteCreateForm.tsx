"use client";

import { useState, useEffect, useRef, FormEvent } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { getSourceLinkIdFromQuery } from "@/lib/tabs";
import { ApiError, NoteCreate, SavedLinkRead } from "@/lib/types";

export interface NoteCreateFormProps {
  links: SavedLinkRead[];
  onCreate: (data: NoteCreate) => Promise<unknown>;
  isCreating?: boolean;
}

export function NoteCreateForm({
  links,
  onCreate,
  isCreating = false,
}: NoteCreateFormProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceLinkId, setSourceLinkId] = useState("");
  const [error, setError] = useState("");
  const preselected = useRef(false);

  // FR-009: arriving with ?source_link_id=... preselects that link (only if it
  // still exists — a deleted source link must not leave a stale selection).
  useEffect(() => {
    if (preselected.current) return;
    const id = getSourceLinkIdFromQuery();
    if (id && links.some((link) => link.id === id)) {
      setSourceLinkId(id);
      preselected.current = true;
    }
  }, [links]);

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
    if (content.length > 100000) {
      setError("Note content must be 100000 characters or less.");
      return;
    }

    try {
      await onCreate({
        title: title.trim(),
        content: content.trim(),
        source_link_id: sourceLinkId || null,
      });
      setTitle("");
      setContent("");
      setSourceLinkId("");
      preselected.current = true;
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
      aria-label="Create a new note"
      className="flex flex-col gap-4 border border-border rounded-lg p-4"
      noValidate
    >
      <Input
        label="Title"
        name="title"
        required
        maxLength={200}
        placeholder="Note title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <div className="flex flex-col gap-2">
        <label
          htmlFor="note-content"
          className="text-sm font-medium text-foreground"
        >
          Content (optional)
        </label>
        <textarea
          id="note-content"
          name="content"
          rows={3}
          maxLength={100000}
          placeholder="Note content (optional)"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="rounded border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label
          htmlFor="note-source-link"
          className="text-sm font-medium text-foreground"
        >
          Source link (optional)
        </label>
        <select
          id="note-source-link"
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
      <Button type="submit" isLoading={isCreating}>
        Add note
      </Button>
    </form>
  );
}
