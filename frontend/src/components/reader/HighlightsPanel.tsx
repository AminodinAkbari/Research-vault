"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { SparkleIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { ExplainAnchor } from "@/components/reader/ExplainCard";
import { highlightColorLabel, resolveHighlightColor } from "@/lib/constants";
import { ApiError, HighlightRead } from "@/lib/types";

export interface HighlightsPanelProps {
  highlights: HighlightRead[];
  isLoading?: boolean;
  isError?: boolean;
  deleteHighlight: (highlightId: string) => Promise<void>;
  isDeleting?: boolean;
  /** Explain this highlight's text with the AI (anchor = the clicked button). */
  onExplain: (highlight: HighlightRead, anchor: ExplainAnchor) => void;
}

export function HighlightsPanel({
  highlights,
  isLoading = false,
  isError = false,
  deleteHighlight,
  isDeleting = false,
  onExplain,
}: HighlightsPanelProps) {
  const [pendingDelete, setPendingDelete] = useState<HighlightRead | null>(
    null
  );
  const [error, setError] = useState("");
  const reduce = useReducedMotion();
  const firstRender = useRef(true);

  // Step 2: auto-scroll refs
  const listRef = useRef<HTMLDivElement>(null);
  const prevCount = useRef(highlights.length);

  useEffect(() => {
    firstRender.current = false;
  }, []);

  // Step 2: scroll the list when a new highlight is added
  useEffect(() => {
    const el = listRef.current;
    if (el && highlights.length > prevCount.current) {
      el.scrollTo({
        top: el.scrollHeight, // change to 0 if newest highlights are at the TOP
        behavior: reduce ? "auto" : "smooth",
      });
    }
    prevCount.current = highlights.length;
  }, [highlights.length, reduce]);

  // Step 3: jump to the highlight inside the article
  const scrollToMark = (highlightId: string) => {
    document
      .querySelector(`mark[data-highlight-id="${highlightId}"]`)
      ?.scrollIntoView({
        behavior: reduce ? "auto" : "smooth",
        block: "center",
      });
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setError("");
    try {
      await deleteHighlight(pendingDelete.id);
      setPendingDelete(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Session expired - please sign in again");
      } else {
        setError("Something went wrong. Please try again.");
      }
    }
  };

  if (isError) {
    return (
      <aside aria-label="Highlights" className="sheet p-5">
        <h2 className="text-base font-semibold tracking-tight text-foreground">
          Highlights
        </h2>
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
      className="sheet flex max-h-[inherit] flex-col p-5"
    >
      <div className="flex shrink-0 items-center justify-between gap-2">
        <h2 className="text-base font-semibold tracking-tight text-foreground">
          Highlights
        </h2>
        {highlights.length > 0 && (
          <span
            key={highlights.length}
            className="animate-popIn inline-flex h-6 min-w-6 items-center justify-center rounded-pill bg-accent/10 px-1.5 font-mono text-xs font-medium text-accent"
          >
            {highlights.length}
          </span>
        )}
      </div>

      <div
        id="highlights-list"
        ref={listRef}
        aria-live="polite"
        className="-mx-2 mt-1 min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 pb-1 [scrollbar-gutter:stable]"
      >
        {isLoading ? (
          <p aria-busy="true" className="mt-3 text-sm text-muted-foreground">
            Loading highlights…
          </p>
        ) : highlights.length === 0 ? (
          <EmptyState
            title="No highlights yet"
            description="Select any text above to save it as a highlight."
            className="py-10"
          />
        ) : (
          <ul className="mt-4 m-0 flex list-none flex-col gap-3 p-0">
            <AnimatePresence initial={false}>
              {highlights.map((highlight, index) => (
                <motion.li
                  key={highlight.id}
                  initial={
                    reduce ? false : { opacity: 0, y: -8, scale: 0.98 }
                  }
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{
                    opacity: 0,
                    scale: 0.97,
                    transition: { duration: 0.15 },
                  }}
                  transition={{
                    type: "spring",
                    stiffness: 420,
                    damping: 30,
                    delay:
                      reduce || !firstRender.current ? 0 : index * 0.05,
                  }}
                  className="group relative flex flex-col gap-2 rounded-lg border border-border bg-surface/60 p-3 transition-colors hover:border-foreground/15"
                >
                  <span
                    aria-hidden="true"
                    className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full"
                    style={{
                      backgroundColor: resolveHighlightColor(highlight.color),
                    }}
                  />

                  {/* Step 3: clickable area (quote + annotation) */}
                  <button
                    type="button"
                    onClick={() => scrollToMark(highlight.id)}
                    title="Show in article"
                    className="flex w-full cursor-pointer flex-col gap-2 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="block border-l-2 border-accent/40 pl-3 font-reading text-[15px] leading-relaxed text-foreground">
                      {highlight.selected_text}
                    </span>
                    {highlight.annotation && (
                      <span className="block pl-3 text-sm leading-relaxed text-muted-foreground">
                        {highlight.annotation}
                      </span>
                    )}
                  </button>

                  <div className="flex items-center gap-2 pl-3">
                    <span
                      data-testid="highlight-color-swatch"
                      aria-hidden="true"
                      className="inline-block h-4 w-4 rounded-pill border border-border"
                      style={{
                        backgroundColor: resolveHighlightColor(highlight.color),
                      }}
                    />
                    <span className="font-mono text-xs text-muted-foreground">
                      {highlightColorLabel(highlight.color)}
                    </span>
                    <div className="ml-auto flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground hover:text-danger"
                        onClick={() => setPendingDelete(highlight)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-3 shrink-0 text-sm text-danger">
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