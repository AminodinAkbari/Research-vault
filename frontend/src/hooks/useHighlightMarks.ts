"use client";

import { useEffect, useRef } from "react";
import { applyMarks, MarkSpec } from "@/lib/highlightMarks";

export type HighlightMark = MarkSpec;

/**
 * Apply saved highlights as marks over the article, and re-apply them whenever
 * the article mounts or the highlights list changes (FR-024).
 *
 * Marks can also be wiped from the DOM by an external mutation (e.g. the
 * article's `innerHTML` being reset) while the highlights list — and thus the
 * React signature — stays identical. In that case `applyMarks` would never
 * re-run and the highlights would stay invisible until a page reload. A
 * MutationObserver watches the article and re-applies the marks whenever they
 * disappear while saved highlights still exist.
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
  const prevSignature = useRef<string | null>(null);
  const observerRef = useRef<MutationObserver | null>(null);
  // Guard against re-entrancy: applyMarks mutates the DOM, which would
  // otherwise re-trigger the observer and loop forever.
  const applyingRef = useRef(false);

  const applyIfNeeded = () => {
    if (!article || applyingRef.current) return;
    const existing = article.querySelectorAll("mark.highlight");
    if (
      signature !== prevSignature.current ||
      (list.length > 0 && existing.length === 0)
    ) {
      applyingRef.current = true;
      prevSignature.current = signature;
      applyMarks(article, list);
      applyingRef.current = false;
    }
  };

  useEffect(() => {
    if (!article) return;
    applyIfNeeded();

    observerRef.current?.disconnect();
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "childList") {
          // Recover when marks are wiped externally and highlights still exist.
          if (list.length > 0 && article.querySelectorAll("mark.highlight").length === 0) {
            applyIfNeeded();
            break;
          }
        }
      }
    });
    observer.observe(article, { childList: true, subtree: true });
    observerRef.current = observer;

    return () => {
      observer.disconnect();
    };
  }, [article, list, signature]);
}
