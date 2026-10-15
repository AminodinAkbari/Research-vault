"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, useReducedMotion } from "motion/react";
import {
  ArrowsClockwiseIcon,
  NotePencilIcon,
  SparkleIcon,
  XIcon,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { LoadingSkeleton } from "@/components/ui/EmptyState";

/** Viewport-relative rect the card anchors to (same shape as a selection rect). */
export interface ExplainAnchor {
  top: number;
  left: number;
  bottom: number;
}

export interface ExplainCardProps {
  quote: string;
  anchor: ExplainAnchor;
  isPending: boolean;
  explanation: string | null;
  error: string | null;
  isSavingNote: boolean;
  noteSaved: boolean;
  onRetry: () => void;
  onSaveNote: () => void;
  onClose: () => void;
}

const CARD_WIDTH = 320;
const QUOTE_LIMIT = 240;

const CLOSE_CLASSES =
  "flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 transition-colors";

/**
 * Floating AI explanation card. Anchored to the text that triggered it (like
 * HighlightPopup) so the reader's scroll position never moves, rendered
 * through a portal so it overlays the article without reflowing it.
 */
export function ExplainCard({
  quote,
  anchor,
  isPending,
  explanation,
  error,
  isSavingNote,
  noteSaved,
  onRetry,
  onSaveNote,
  onClose,
}: ExplainCardProps) {
  const reduce = useReducedMotion();

  // FR-023-style dismissal for keyboard users
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (typeof document === "undefined") return null;

  // Clamp horizontally so the card never overflows the viewport when the
  // trigger sits near the right edge (e.g. the highlights panel).
  const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
  const width = Math.min(CARD_WIDTH, viewportWidth - 32);
  const left = Math.min(
    Math.max(anchor.left + window.scrollX, window.scrollX + 16),
    window.scrollX + viewportWidth - width - 16
  );

  const position = {
    position: "absolute" as const,
    top: anchor.bottom + window.scrollY + 8,
    left,
    width,
    maxWidth: "calc(100vw - 2rem)",
    zIndex: 1000,
    transformOrigin: "top left",
  };

  const displayQuote =
    quote.length > QUOTE_LIMIT ? `${quote.slice(0, QUOTE_LIMIT).trimEnd()}…` : quote;

  // Skeleton also covers the first paint before the mutation reports pending.
  const showSkeleton = isPending || (!error && !explanation);

  return createPortal(
    <motion.section
      id="explain-card"
      aria-label="AI explanation"
      style={position}
      initial={reduce ? false : { opacity: 0, y: -6, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 480, damping: 32, mass: 0.7 }}
      className="glass max-h-[70vh] overflow-y-auto rounded-xl p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-sm font-medium tracking-tight text-foreground">
          <Icon size={15} weight="bold" className="text-accent">
            <SparkleIcon />
          </Icon>
          AI explanation
        </span>
        <button
          type="button"
          aria-label="Close explanation"
          onClick={onClose}
          className={CLOSE_CLASSES}
        >
          <XIcon size={14} weight="bold" aria-hidden="true" />
        </button>
      </div>

      <figure className="m-0 mt-3 border-l-2 border-accent/40 pl-3">
        <blockquote className="m-0 font-reading text-[15px] leading-relaxed text-muted-foreground">
          {displayQuote}
        </blockquote>
      </figure>

      <div aria-live="polite" className="mt-3">
        {showSkeleton ? (
          <LoadingSkeleton lines={2} data-testid="explain-skeleton" />
        ) : error ? (
          <div className="flex flex-col items-start gap-3">
            <p role="alert" className="m-0 text-sm leading-relaxed text-danger">
              {error}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetry}
              leftIcon={
                <Icon size={14} weight="bold">
                  <ArrowsClockwiseIcon />
                </Icon>
              }
              className="gap-1.5"
            >
              Retry
            </Button>
          </div>
        ) : (
          <>
            <p className="m-0 text-sm leading-relaxed text-foreground">
              {explanation}
            </p>
            <div className="mt-3.5 flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                onClick={onSaveNote}
                isLoading={isSavingNote}
                disabled={noteSaved}
                leftIcon={
                  <Icon size={14} weight="bold">
                    <NotePencilIcon />
                  </Icon>
                }
                className="gap-1.5"
              >
                {noteSaved ? "Saved" : "Save as Note"}
              </Button>
            </div>
          </>
        )}
      </div>
    </motion.section>,
    document.body
  );
}
