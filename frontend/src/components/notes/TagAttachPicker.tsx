"use client";

import { useState } from "react";
import { ApiError, TagRead } from "@/lib/types";

export interface TagAttachPickerProps {
  tags: TagRead[];
  attachedTagIds: string[];
  onAttach: (tagId: string) => Promise<unknown>;
}

export function TagAttachPicker({
  tags,
  attachedTagIds,
  onAttach,
}: TagAttachPickerProps) {
  const [error, setError] = useState("");
  const [pendingId, setPendingId] = useState("");

  const available = tags.filter((tag) => !attachedTagIds.includes(tag.id));

  const handleAttach = async (tagId: string) => {
    setError("");
    setPendingId(tagId);
    try {
      await onAttach(tagId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setPendingId("");
    }
  };

  if (available.length === 0) {
    return (
      <p className="text-sm text-muted-foreground mt-2">
        All project tags are already attached to this note.
      </p>
    );
  }

  return (
    <div className="mt-2">
      <div
        role="listbox"
        aria-label="Available tags to attach"
        className="flex flex-wrap gap-2"
      >
        {available.map((tag) => (
          <button
            key={tag.id}
            type="button"
            onClick={() => handleAttach(tag.id)}
            disabled={pendingId === tag.id}
            className="rounded-pill border border-border bg-background px-2 py-0.5 text-xs font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            + {tag.name}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger mt-2">
          {error}
        </p>
      )}
    </div>
  );
}
