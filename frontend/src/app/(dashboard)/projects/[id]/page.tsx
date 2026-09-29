"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProjects } from "@/hooks/useProjects";
import { NotFound } from "@/components/layout/NotFound";
import { NotesPanel } from "@/components/notes/NotesPanel";
import { TagsPanel } from "@/components/tags/TagsPanel";
import { TabBar } from "@/components/ui/TabBar";
import { TABS, getInitialTab, type TabId } from "@/lib/tabs";

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = params.id as string;
  const { projects, isLoading } = useProjects();

  const project = projects.find((p) => p.id === projectId);
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab);

  // Sync with URL hash changes
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.substring(1);
      const tab = TABS.find((t) => t.hash === `#${hash}`);
      if (tab) setActiveTab(tab.id);
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  if (isLoading) {
    return (
      <p role="status" aria-busy="true" className="text-muted-foreground">
        Loading project…
      </p>
    );
  }

  if (!project) {
    return <NotFound message="Project not found or you don't have access to it." />;
  }

  return (
    <div className="space-y-6">
      {/* Header with back navigation and project info */}
      <div>
        <Link
          href="/dashboard"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors mb-2 inline-block"
        >
          ← Back to projects
        </Link>
        <h1 className="text-2xl font-bold text-foreground">{project.name}</h1>
        <p className="text-muted-foreground mt-1">
          {project.description || "No description yet."}
        </p>
      </div>

      {/* Search box area */}
      <div>
        <div className="flex gap-2">
          <input
            type="search"
            placeholder="Search notes & links…"
            aria-label="Full-text search"
            className="flex-1 h-10 px-3 rounded border border-border bg-background text-sm"
          />
          <button
            type="button"
            className="h-10 px-4 rounded border border-border bg-background text-sm hover:bg-muted"
          >
            Search
          </button>
        </div>
        <div id="collected-search-results" className="mt-3" />
      </div>

      {/* Export button */}
      <div className="flex justify-end">
        <a
          href={`http://localhost:8000/api/v1/projects/${project.id}/export/markdown`}
          download
          className="text-sm text-accent hover:underline"
        >
          Export as Markdown
        </a>
      </div>

      {/* Tag filter results area */}
      <div id="tag-filter-results" aria-live="polite" className="min-h-0" />

      {/* Tabs */}
      <TabBar
        tabs={TABS.map((t) => ({ id: t.id, label: t.label }))}
        activeTab={activeTab}
        onTabChange={(tabId) => setActiveTab(tabId as TabId)}
      />

      {/* Tab panels */}
      <div className="mt-6">
        <div id="notes-panel" role="tabpanel" aria-labelledby="notes-panel-tab" hidden={activeTab !== "notes-panel"}>
          <NotesPanel projectId={project.id} />
        </div>
        <div id="links-panel" role="tabpanel" aria-labelledby="links-panel-tab" hidden={activeTab !== "links-panel"}>
          <div className="text-muted-foreground">Links panel — Phase 6</div>
        </div>
        <div id="websearch-panel" role="tabpanel" aria-labelledby="websearch-panel-tab" hidden={activeTab !== "websearch-panel"}>
          <div className="text-muted-foreground">Web Search panel — Phase 6</div>
        </div>
        <div id="tags-panel" role="tabpanel" aria-labelledby="tags-panel-tab" hidden={activeTab !== "tags-panel"}>
          <TagsPanel projectId={project.id} />
        </div>
      </div>
    </div>
  );
}