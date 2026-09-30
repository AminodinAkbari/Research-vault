"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { ApiError, SavedLinkRead } from "@/lib/types";
import { computeGlobalOffset } from "@/lib/highlightMarks";
import { resolveHighlightColor } from "@/lib/constants";
import { useProjects } from "@/hooks/useProjects";
import { useHighlights } from "@/hooks/useHighlights";
import { useHighlightMarks } from "@/hooks/useHighlightMarks";
import {
  HighlightPopup,
  HighlightSavePayload,
  HighlightSelection,
} from "@/components/reader/HighlightPopup";
import { HighlightsPanel } from "@/components/reader/HighlightsPanel";
import { NotFound } from "@/components/layout/NotFound";
import { Button } from "@/components/ui/Button";

export default function LinkReaderPage() {
  const params = useParams();
  const projectId = params.id as string;
  const linkId = params.linkId as string;

  const { projects, isLoading: projectsLoading } = useProjects();
  const project = projects.find((p) => p.id === projectId);

  const linkQuery = useQuery({
    queryKey: ["link", projectId, linkId],
    queryFn: () => apiFetch(endpoints.link(projectId, linkId), SavedLinkRead),
    enabled: !!projectId && !!linkId,
    staleTime: 15000,
  });
  const link = linkQuery.data;

  const {
    highlights,
    isLoading: highlightsLoading,
    isError: highlightsError,
    createHighlight,
    deleteHighlight,
    isDeleting,
  } = useHighlights(projectId, linkId);

  const [articleEl, setArticleEl] = useState<HTMLElement | null>(null);
  const setArticleRef = useCallback(
    (node: HTMLElement | null) => setArticleEl(node),
    []
  );
  const [selection, setSelection] = useState<HighlightSelection | null>(null);

  useHighlightMarks(articleEl, highlights);

  // FR-023: releasing a selection inside the article opens the popup
  useEffect(() => {
    if (!articleEl) return;

    const handleMouseUp = (event: MouseEvent) => {
      const target = event.target;
      if (
        target instanceof Element &&
        target.closest("#highlight-popup") !== null
      ) {
        return;
      }

      const domSelection = window.getSelection();
      const text = domSelection ? domSelection.toString().trim() : "";
      if (!text || !domSelection || !domSelection.anchorNode) return;
      if (!articleEl.contains(domSelection.anchorNode)) return;

      const range = domSelection.getRangeAt(0);
      const startOffset = computeGlobalOffset(
        articleEl,
        range.startContainer,
        range.startOffset
      );
      const endOffset = computeGlobalOffset(
        articleEl,
        range.endContainer,
        range.endOffset
      );
      if (startOffset === -1 || endOffset === -1 || endOffset <= startOffset) {
        return;
      }

      const rect = range.getBoundingClientRect();
      setSelection({
        text,
        startOffset,
        endOffset,
        range: range.cloneRange(),
        rect: { top: rect.top, left: rect.left, bottom: rect.bottom },
      });
    };

    articleEl.addEventListener("mouseup", handleMouseUp);
    return () => articleEl.removeEventListener("mouseup", handleMouseUp);
  }, [articleEl]);

  const handleSave = async (payload: HighlightSavePayload) => {
    if (!selection) return;

    await createHighlight({
      selected_text: selection.text,
      annotation: payload.annotation || null,
      start_offset: selection.startOffset,
      end_offset: selection.endOffset,
      color: payload.color,
    });

    // Instant visual feedback while the list round-trips (FR-024)
    try {
      const contents = selection.range.extractContents();
      const tempMark = document.createElement("mark");
      tempMark.className = "highlight temp-highlight";
      tempMark.style.backgroundColor = resolveHighlightColor(payload.color);
      tempMark.appendChild(contents);
      selection.range.insertNode(tempMark);
    } catch {
      // The marks engine repaints from the saved list regardless
    }

    setSelection(null);
  };

  if (projectsLoading || (linkQuery.isLoading && !link)) {
    return (
      <p role="status" aria-busy="true" className="text-muted-foreground">
        Loading article…
      </p>
    );
  }

  if (linkQuery.isError) {
    const status =
      linkQuery.error instanceof ApiError ? linkQuery.error.status : null;
    if (status === 401) {
      return (
        <NotFound
          title="Session expired"
          message="Session expired — please sign in again."
          actionLabel="Go to login"
          actionHref="/login"
        />
      );
    }
    if (status === 404 || status === 403) {
      return (
        <NotFound
          title="Link not found"
          message="This link doesn't exist or you don't have access to it."
          actionLabel="Back to projects"
          actionHref="/dashboard"
        />
      );
    }
    return (
      <div className="text-center py-12">
        <p className="text-danger">Failed to load this article.</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => linkQuery.refetch()}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (!project) {
    return (
      <NotFound message="Project not found or you don't have access to it." />
    );
  }

  if (!link) {
    return (
      <NotFound
        title="Link not found"
        message="This link doesn't exist or you don't have access to it."
        actionLabel="Back to projects"
        actionHref={`/projects/${projectId}`}
      />
    );
  }

  const hasContent =
    link.extraction_status === "completed" && !!link.extracted_content;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <Link
          href={`/projects/${projectId}`}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          ← Back to {project.name}
        </Link>
        <Link
          href={`/projects/${projectId}?source_link_id=${linkId}#notes-panel`}
          className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted"
        >
          + Add note about this
        </Link>
      </div>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">{link.title}</h1>
        <p className="text-sm">
          <a
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all text-accent hover:underline"
          >
            {link.url}
          </a>
        </p>
      </header>

      {hasContent ? (
        <div
          id="reader-article"
          ref={setArticleRef}
          className="space-y-4 text-sm leading-6 text-foreground [&_a]:break-words [&_a]:text-accent [&_a]:underline [&_blockquote]:m-0 [&_h2]:text-lg [&_h2]:font-semibold [&_ul]:m-0 [&_ul]:list-disc [&_ul]:pl-5"
          dangerouslySetInnerHTML={{ __html: link.extracted_content ?? "" }}
        />
      ) : (
        <p className="text-muted-foreground">Content not yet extracted.</p>
      )}

      <HighlightsPanel
        highlights={highlights}
        isLoading={highlightsLoading}
        isError={highlightsError}
        deleteHighlight={deleteHighlight}
        isDeleting={isDeleting}
      />

      {selection && articleEl && (
        <HighlightPopup
          selection={selection}
          onSave={handleSave}
          onClose={() => setSelection(null)}
        />
      )}
    </div>
  );
}
