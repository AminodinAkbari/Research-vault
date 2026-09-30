/**
 * Highlight color constants.
 * Source of truth: app/templates/links/read.html (colorMap) + spec Design Direction.
 * The six highlight colors are exempt from the one-accent lock.
 */

import type { HighlightColor } from "./types";

export const HIGHLIGHT_COLOR_HEX: Record<HighlightColor, string> = {
  yellow: "#fff59d",
  blue: "#b3e5fc",
  green: "#c8e6c9",
  orange: "#ffccbc",
  purple: "#e1bee7",
  grey: "#f0f0f0",
};

export const HIGHLIGHT_COLOR_NAMES: HighlightColor[] = [
  "yellow",
  "blue",
  "green",
  "orange",
  "purple",
  "grey",
];

export const DEFAULT_HIGHLIGHT_COLOR = HIGHLIGHT_COLOR_HEX.yellow;

const HEX_COLOR = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

/**
 * Named colors map to their hex value; legacy/unknown stored colors (e.g. raw
 * hex) render as-is when valid; anything else falls back to the default yellow.
 */
export function resolveHighlightColor(color?: string | null): string {
  if (color && color in HIGHLIGHT_COLOR_HEX) {
    return HIGHLIGHT_COLOR_HEX[color as HighlightColor];
  }
  if (color && HEX_COLOR.test(color)) {
    return color;
  }
  return DEFAULT_HIGHLIGHT_COLOR;
}

/** Human-readable label for a stored color ("" when the color is legacy/unknown). */
export function highlightColorLabel(color?: string | null): string {
  if (color && color in HIGHLIGHT_COLOR_HEX) {
    return color.charAt(0).toUpperCase() + color.slice(1);
  }
  if (color && HEX_COLOR.test(color)) {
    return color;
  }
  return "Yellow";
}
