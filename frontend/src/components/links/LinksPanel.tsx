"use client";

import { useState } from "react";
import Link from "next/link";
import { useLinks } from "@/hooks/useLinks";
import { useExtractionPolling } from "@/hooks/useExtractionPolling";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError, SavedLinkRead } from "@/lib/types";

export interface LinksPanelProps {
  projectId: string;
}

const STATUS_LABEL: Record<SavedLinkRead["extraction_status"], string> = {
  pending: "Pending",
  completed: "Completed",
  failed: "Failed",
};

const STATUS_VARIANT: Record<
  SavedLinkRead["extraction_status"],
  "warning" | "success" | "danger"
> = {
  pending: "warning",
  completed: "success",
  failed: "danger",
};

function truncateUrl(url: string): string {
  return url.length > 80 ? `${url.slice(0, 80)}…` : url;
}

export function LinksPanel({ projectId }: LinksPanelProps) {
  const { links, isLoading, isError, deleteLink, isDeleting } =
    useLinks(projectId);
  const [pendingDelete, setPendingDelete] = useState<SavedLinkRead | null>(
    null
  );
  const [error, setError] = useState("");

  useExtractionPolling(projectId, links);

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setError("");
    try {
      await deleteLink(pendingDelete.id);
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
      <div className="text-center py-12">
        <p className="text-danger">Failed to load links.</p>
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
    <div className="space-y-4">
      <div aria-live="polite">
        {isLoading ? (
          <p aria-busy="true" className="text-muted-foreground">
            Loading links…
          </p>
        ) : links.length === 0 ? (
          <EmptyState
            title="No links saved yet."
            description="Use the Web Search tab to find and save some."
          />
        ) : (
          <ul className="flex flex-col gap-4 list-none p-0 m-0">
            {links.map((link) => (
              <li key={link.id}>
                <article
                  id={`link-${link.id}`}
                  className="border border-border rounded-lg p-4 bg-background"
                >
                  <header className="flex items-center justify-between gap-3">
                    <Link
                      href={`/projects/${projectId}/links/${link.id}/read`}
                      className="font-semibold text-foreground hover:text-accent transition-colors"
                    >
                      {link.title}
                    </Link>
                    <Badge variant={STATUS_VARIANT[link.extraction_status]}>
                      {STATUS_LABEL[link.extraction_status]}
                    </Badge>
                  </header>

                  <p className="mt-1 text-sm">
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-accent hover:underline"
                    >
                      {truncateUrl(link.url)}
                    </a>
                  </p>

                  {link.snippet && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {link.snippet}
                    </p>
                  )}

                  <div
                    aria-label="Tags on this link"
                    className="mt-2 flex flex-wrap items-center gap-2"
                  >
                    {link.tags.length === 0 ? (
                      <span className="text-sm text-muted-foreground">
                        No tags
                      </span>
                    ) : (
                      link.tags.map((tag) => (
                        <Badge key={tag.id}>{tag.name}</Badge>
                      ))
                    )}
                  </div>

                  <div className="mt-3 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPendingDelete(link)}
                    >
                      Delete
                    </Button>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete link"
        message="Delete this saved link?"
        confirmLabel="Delete"
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => {
          setPendingDelete(null);
          setError("");
        }}
      />
    </div>
  );
}
