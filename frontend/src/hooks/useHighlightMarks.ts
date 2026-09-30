"use client";

import { useEffect } from "react";
import { applyMarks, MarkSpec } from "@/lib/highlightMarks";

export type HighlightMark = MarkSpec;

/**
 * Apply saved highlights as marks over the article, and re-apply them whenever
 * the article mounts or the highlights list changes (FR-024).
 */
export function useHighlightMarks(
  article: HTMLElement | null,
  highlights: HighlightMark[] | undefined
): void {
  const list = highlights ?? [];
  const signature = list
    .map(
      (h) =>
        `${h.id}:${h.start_offset}:${h.end_offset}:${h.color ?? ""}`
    )
    .join("|");

  useEffect(() => {
    if (!article) return;
    applyMarks(article, list);
    // The signature covers id/offsets/color, so re-renders with identical
    // highlights don't tear down and rebuild every mark.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [article, signature]);
}
