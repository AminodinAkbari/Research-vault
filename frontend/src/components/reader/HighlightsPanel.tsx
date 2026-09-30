"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { highlightColorLabel, resolveHighlightColor } from "@/lib/constants";
import { ApiError, HighlightRead } from "@/lib/types";

export interface HighlightsPanelProps {
  highlights: HighlightRead[];
  isLoading?: boolean;
  isError?: boolean;
  deleteHighlight: (highlightId: string) => Promise<void>;
  isDeleting?: boolean;
}

export function HighlightsPanel({
  highlights,
  isLoading = false,
  isError = false,
  deleteHighlight,
  isDeleting = false,
}: HighlightsPanelProps) {
  const [pendingDelete, setPendingDelete] = useState<HighlightRead | null>(
    null
  );
  const [error, setError] = useState("");

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setError("");
    try {
      await deleteHighlight(pendingDelete.id);
      setPendingDelete(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else {
        setError("Something went wrong. Please try again.");
      }
    }
  };

  if (isError) {
    return (
      <aside
        aria-label="Highlights"
        className="rounded-lg border border-border bg-background p-4"
      >
        <h2 className="text-lg font-semibold text-foreground">Highlights</h2>
        <div className="text-center py-8">
          <p className="text-danger">Failed to load highlights.</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      </aside>
    );
  }

  return (
    <aside
      aria-label="Highlights"
      className="rounded-lg border border-border bg-background p-4"
    >
      <h2 className="text-lg font-semibold text-foreground">Highlights</h2>

      <div id="highlights-list" aria-live="polite">
        {isLoading ? (
          <p aria-busy="true" className="mt-2 text-muted-foreground">
            Loading highlights…
          </p>
        ) : highlights.length === 0 ? (
          <EmptyState
            title="No highlights yet"
            description="Select any text above to save it as a highlight."
          />
        ) : (
          <ul className="mt-3 flex list-none flex-col gap-4 p-0 m-0">
            {highlights.map((highlight) => (
              <li
                key={highlight.id}
                className="flex flex-col gap-2 border-b border-border pb-4 last:border-b-0 last:pb-0"
              >
                <blockquote className="m-0 border-l-2 border-accent pl-3 text-sm text-foreground">
                  {highlight.selected_text}
                </blockquote>

                {highlight.annotation && (
                  <p className="m-0 text-sm text-muted-foreground">
                    {highlight.annotation}
                  </p>
                )}

                <div className="flex items-center gap-2">
                  <span
                    data-testid="highlight-color-swatch"
                    aria-hidden="true"
                    className="inline-block h-4 w-4 rounded-pill border border-border"
                    style={{
                      backgroundColor: resolveHighlightColor(highlight.color),
                    }}
                  />
                  <span className="text-xs text-muted-foreground">
                    {highlightColorLabel(highlight.color)}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="ml-auto"
                    onClick={() => setPendingDelete(highlight)}
                  >
                    Remove
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Remove highlight"
        message="Remove this highlight?"
        confirmLabel="Remove"
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => {
          setPendingDelete(null);
          setError("");
        }}
      />
    </aside>
  );
}
