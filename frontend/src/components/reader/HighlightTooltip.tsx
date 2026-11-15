"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, useReducedMotion } from "motion/react";
import { HighlightRead } from "@/lib/types";

export interface HighlightTooltipProps {
  article: HTMLElement | null;
  highlights: HighlightRead[];
}

/**
 * Floating tooltip that shows a highlight's saved annotation when the user
 * hovers over its `<mark>` in the reader article.
 *
 * Marks are applied imperatively by `useHighlightMarks` (direct DOM
 * manipulation), so React doesn't own the `<mark>` nodes. We attach bubbling
 * `mouseover`/`mouseout` listeners to the article element and look the
 * annotation up by `data-highlight-id`. Only highlights that actually have a
 * saved annotation show a tooltip.
 */
export function HighlightTooltip({ article, highlights }: HighlightTooltipProps) {
  const reduce = useReducedMotion();
  const [visible, setVisible] = useState(false);
  const [anchor, setAnchor] = useState<{ top: number; left: number } | null>(null);
  const [annotation, setAnnotation] = useState("");
  const tooltipRef = useRef<HTMLDivElement>(null);
  const hideTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const clearHideTimeout = useCallback(() => {
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    clearHideTimeout();
    setVisible(false);
    setAnchor(null);
    setAnnotation("");
  }, [clearHideTimeout]);

  const scheduleHide = useCallback(
    (delay = 150) => {
      clearHideTimeout();
      hideTimeoutRef.current = setTimeout(() => {
        hide();
      }, delay);
    },
    [clearHideTimeout, hide]
  );

  // id -> annotation, kept in sync so the listener reads fresh data without
  // re-attaching on every highlights change.
  const annotationsById = useRef<Map<string, string>>(new Map());
  useEffect(() => {
    annotationsById.current = new Map(
      highlights.filter((h) => h.annotation).map((h) => [h.id, h.annotation!])
    );
  }, [highlights]);

  const handleMouseOver = useCallback(
    (event: MouseEvent) => {
      if (!article) return;
      const target = event.target as HTMLElement | null;
      const mark = target?.closest<HTMLElement>("mark.highlight[data-highlight-id]");
      const id = mark?.dataset.highlightId ?? null;
      const annotation = id ? annotationsById.current.get(id) ?? null : null;
      if (!id || !annotation) {
        // If we're not on a mark, schedule hide (might be moving from mark to whitespace)
        // Only hide if we aren't moving into the tooltip itself
        const related = event.relatedTarget as HTMLElement | null;
        if (!tooltipRef.current?.contains(related)) {
          scheduleHide(150);
        }
        return;
      }
      clearHideTimeout();
      const rect = mark!.getBoundingClientRect();
      const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
      const width = Math.min(320, viewportWidth - 32);
      // Center horizontally over the highlight
      let left = rect.left + rect.width / 2 - width / 2 + window.scrollX;
      left = Math.max(
        window.scrollX + 16,
        Math.min(left, window.scrollX + viewportWidth - width - 16)
      );
      setAnchor({ top: rect.top + window.scrollY - 12, left });
      setAnnotation(annotation);
      setVisible(true);
    },
    [article, scheduleHide, clearHideTimeout]
  );

  const handleMouseOut = useCallback(
    (event: MouseEvent) => {
      if (!article) return;
      const target = event.target as HTMLElement | null;
      const mark = target?.closest<HTMLElement>("mark.highlight[data-highlight-id]");
      const id = mark?.dataset.highlightId ?? null;
      if (!id) return;
      const related = event.relatedTarget as HTMLElement | null;
      if (related?.closest<HTMLElement>("mark.highlight[data-highlight-id]")?.dataset.highlightId === id) {
        return; // still on the same mark
      }
      if (tooltipRef.current?.contains(related)) {
        return; // moving to the tooltip
      }
      scheduleHide(150);
    },
    [article, scheduleHide]
  );

  useEffect(() => {
    if (!article) return;
    article.addEventListener("mouseover", handleMouseOver);
    article.addEventListener("mouseout", handleMouseOut);
    return () => {
      article.removeEventListener("mouseover", handleMouseOver);
      article.removeEventListener("mouseout", handleMouseOut);
      clearHideTimeout();
    };
  }, [article, handleMouseOver, handleMouseOut, clearHideTimeout]);

  if (!visible || !anchor || !annotation) return null;

  const viewportWidth = document.documentElement.clientWidth || window.innerWidth;

  const position = {
    position: "absolute" as const,
    top: anchor.top,
    left: anchor.left,
    width: Math.min(320, viewportWidth - 32),
    maxWidth: "calc(100vw - 2rem)",
    zIndex: 1000,
  };

  return createPortal(
    <motion.div
      ref={tooltipRef}
      id="highlight-tooltip"
      role="tooltip"
      style={position}
      onMouseEnter={clearHideTimeout}
      onMouseLeave={() => scheduleHide(150)}
      initial={reduce ? { opacity: 0, y: "-100%" } : { opacity: 0, y: "-95%" }}
      animate={{ opacity: 1, y: "-100%" }}
      transition={{ type: "spring", stiffness: 480, damping: 32, mass: 0.7 }}
      className="z-1000 rounded-lg border border-border bg-surface px-3 py-2 text-sm leading-relaxed text-foreground shadow-elev-2 text-center"
    >
      {annotation}
    </motion.div>,
    document.body
  );
}
