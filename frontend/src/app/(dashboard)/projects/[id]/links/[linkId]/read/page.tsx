"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

  // Visual only: when the user saves a highlight, paint the (temp or rebuilt)
  // <mark> in with a wipe + glow. The marks engine rebuilds marks on list
  // updates, so the class is (re)applied to the persisted mark here, resuming
  // the animation from the elapsed time so the two marks read as one motion.
  const [lastSaved, setLastSaved] = useState<{
    id: string;
    color: string;
    at: number;
  } | null>(null);
  const animatedIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!lastSaved || !articleEl || animatedIdsRef.current.has(lastSaved.id)) {
      return;
    }
    const mark = articleEl.querySelector<HTMLElement>(
      `mark[data-highlight-id="${lastSaved.id}"]`
    );
    if (!mark || mark.classList.contains("hl-enter")) return;
    const elapsed = Date.now() - lastSaved.at;
    animatedIdsRef.current.add(lastSaved.id);
    mark.classList.add("hl-enter");
    mark.style.setProperty("--hl", lastSaved.color);
    if (elapsed > 0 && elapsed < 700) {
      mark.style.animationDelay = `-${elapsed}ms, -${elapsed}ms`;
    }
  }, [lastSaved, articleEl, highlights]);

  // FR-023 / FR-027: releasing a selection inside the article opens the popup.
  // Mouse users get it on mouseup; keyboard users (selection made with the
  // keyboard, e.g. caret browsing) get it on keyup — no mouse required.
  useEffect(() => {
    if (!articleEl) return;

    const openFromSelection = () => {
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

    const handleMouseUp = (event: MouseEvent) => {
      const target = event.target;
      if (
        target instanceof Element &&
        target.closest("#highlight-popup") !== null
      ) {
        return;
      }
      openFromSelection();
    };

    const handleKeyUp = () => {
      const active = document.activeElement;
      if (active instanceof Element && active.closest("#highlight-popup")) {
        return;
      }
      openFromSelection();
    };

    articleEl.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("keyup", handleKeyUp);
    return () => {
      articleEl.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("keyup", handleKeyUp);
    };
  }, [articleEl]);

  const handleSave = async (payload: HighlightSavePayload) => {
    if (!selection) return;

    const saved = await createHighlight({
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
      tempMark.className = "highlight temp-highlight hl-enter";
      const hex = resolveHighlightColor(payload.color);
      tempMark.style.backgroundColor = hex;
      tempMark.style.setProperty("--hl", hex);
      tempMark.appendChild(contents);
      selection.range.insertNode(tempMark);
    } catch {
      // The marks engine repaints from the saved list regardless
    }

    if (saved?.id) {
      setLastSaved({
        id: saved.id,
        color: resolveHighlightColor(payload.color),
        at: Date.now(),
      });
    }

    setSelection(null);
  };

  if (projectsLoading || (linkQuery.isLoading && !link)) {
    return (
      <div role="status" aria-busy="true" className="flex flex-col items-center justify-center gap-4 py-24 text-muted-foreground">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-accent" />
        <p className="text-sm">Loading article…</p>
      </div>
    );
  }

  if (linkQuery.isError) {
    const status =
      linkQuery.error instanceof ApiError ? linkQuery.error.status : null;
    if (status === 401) {
      return (
        <NotFound
          title="Session expired"
          message="Session expired - please sign in again."
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/projects/${projectId}`}
          className="group inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <span className="transition-transform group-hover:-translate-x-0.5">←</span>
          Back to {project.name}
        </Link>
        <Link
          href={`/projects/${projectId}?source_link_id=${linkId}#notes-panel`}
          className="rounded-md border border-border bg-surface px-3.5 py-2 text-sm font-medium tracking-tight text-foreground shadow-elev-1 transition-all duration-150 hover:bg-muted hover:border-foreground/20 active:scale-[0.98]"
        >
          + Add note about this
        </Link>
      </div>

      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="mx-auto w-full min-w-0 max-w-[760px] space-y-6">
          <header className="space-y-2.5">
            <h1 className="font-reading text-3xl sm:text-4xl font-medium leading-[1.1] tracking-tight text-foreground">
              {link.title}
            </h1>
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="break-all font-mono text-xs text-muted-foreground transition-colors hover:text-accent"
            >
              {link.url}
            </a>
          </header>

          {hasContent ? (
            <div
              id="reader-article"
              ref={setArticleRef}
              // Focusable so keyboard users can reach the article text (FR-027)
              role="region"
              aria-label="Article content"
              tabIndex={0}
              className="sheet px-6 py-8 sm:px-10 sm:py-12 scroll-mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4 focus-visible:ring-offset-background"
              dangerouslySetInnerHTML={{ __html: link.extracted_content ?? "" }}
            />
          ) : (
            <div className="sheet px-6 py-10 sm:px-10 text-muted-foreground">
              <p className="m-0">Content not yet extracted.</p>
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-[760px] max-h-[60vh] xl:max-h-[calc(100vh-7rem)] xl:max-w-none xl:sticky xl:top-24">
          <HighlightsPanel
            highlights={highlights}
            isLoading={highlightsLoading}
            isError={highlightsError}
            deleteHighlight={deleteHighlight}
            isDeleting={isDeleting}
          />
        </div>
      </div>

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
