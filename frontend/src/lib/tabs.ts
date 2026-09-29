/**
 * Tab activation utilities for URL hash and query parameter handling
 */

export type TabId = "notes-panel" | "links-panel" | "websearch-panel" | "tags-panel";

export const TABS: { id: TabId; label: string; hash: string }[] = [
  { id: "notes-panel", label: "Notes", hash: "#notes-panel" },
  { id: "links-panel", label: "Links", hash: "#links-panel" },
  { id: "websearch-panel", label: "Web Search", hash: "#websearch-panel" },
  { id: "tags-panel", label: "Tags", hash: "#tags-panel" },
];

export function getTabFromHash(): TabId | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash;
  const tab = TABS.find((t) => t.hash === hash);
  return tab?.id ?? null;
}

export function getSourceLinkIdFromQuery(): string | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  return params.get("source_link_id");
}

export function activateTab(tabId: TabId): void {
  // Update URL hash without scroll
  history.replaceState(null, "", TABS.find((t) => t.id === tabId)?.hash || "");
}

export function getInitialTab(): TabId {
  // Priority: URL hash > query param > default (Notes)
  const hashTab = getTabFromHash();
  if (hashTab) return hashTab;

  const sourceLinkId = getSourceLinkIdFromQuery();
  if (sourceLinkId) return "notes-panel";

  return "notes-panel";
}