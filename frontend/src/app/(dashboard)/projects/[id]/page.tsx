"use client";

import { useCallback, useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { NoteRead, SavedLinkRead } from "@/lib/types";
import { useProjects } from "@/hooks/useProjects";
import { NotFound } from "@/components/layout/NotFound";
import { NotesPanel } from "@/components/notes/NotesPanel";
import { LinksPanel } from "@/components/links/LinksPanel";
import { WebSearchPanel } from "@/components/search/WebSearchPanel";
import { RoadmapPanel } from "@/components/roadmap/RoadmapPanel";
import { ProjectSearchBox } from "@/components/search/ProjectSearchBox";
import { TagFilterResults } from "@/components/tags/TagFilterResults";
import { TagsPanel } from "@/components/tags/TagsPanel";
import { ExportButton } from "@/components/export/ExportButton";
import { TabBar } from "@/components/ui/TabBar";
import { TABS, getInitialTab, type TabId } from "@/lib/tabs";

interface TagFilter {
  id: string;
  name: string;
}

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = params.id as string;
  const { projects, isLoading } = useProjects();

  const project = projects.find((p) => p.id === projectId);
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab);
  const [tagFilter, setTagFilter] = useState<TagFilter | null>(null);
  const [pendingNoteScroll, setPendingNoteScroll] = useState<string | null>(
    null
  );

  // Shared with the panels above (same query keys ⇒ one request per list)
  const notesQuery = useQuery({
    queryKey: ["notes", projectId],
    queryFn: () => apiFetch(endpoints.notes(projectId), NoteRead.array()),
    staleTime: 15000,
    enabled: !!projectId,
  });
  const linksQuery = useQuery({
    queryKey: ["links", projectId],
    queryFn: () => apiFetch(endpoints.links(projectId), SavedLinkRead.array()),
    staleTime: 15000,
    enabled: !!projectId,
  });

  const handleTagClick = useCallback((tag: TagFilter) => {
    setTagFilter(tag);
  }, []);

  const handleNoteSelect = useCallback((noteId: string) => {
    setActiveTab("notes-panel");
    setPendingNoteScroll(noteId);
  }, []);

  // FR-020: jump to the note once its tab is visible
  useEffect(() => {
    if (!pendingNoteScroll) return;
    document
      .getElementById(`note-${pendingNoteScroll}`)
      ?.scrollIntoView({ block: "start" });
    setPendingNoteScroll(null);
  }, [pendingNoteScroll, activeTab]);

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
      <header className="space-y-2.5">
        <Link
          href="/dashboard"
          className="group inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="transition-transform group-hover:-translate-x-0.5">←</span>
          Back to projects
        </Link>
        <h1 className="font-reading text-3xl sm:text-4xl font-medium leading-[1.1] tracking-tight text-foreground">
          {project.name}
        </h1>
        <p className="text-muted-foreground max-w-2xl">
          {project.description || "No description yet."}
        </p>
      </header>

      {/* Search + export toolbar */}
      <div className="sheet flex flex-col gap-5 p-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 flex-1">
          <ProjectSearchBox
            projectId={project.id}
            onNoteSelect={handleNoteSelect}
          />
        </div>
        <ExportButton projectId={project.id} />
      </div>

      {/* Tag filter results area */}
      {tagFilter && (
        <TagFilterResults
          projectId={project.id}
          tag={tagFilter}
          notes={notesQuery.data ?? []}
          links={linksQuery.data ?? []}
          isLoading={notesQuery.isLoading || linksQuery.isLoading}
          onClear={() => setTagFilter(null)}
          onNoteSelect={handleNoteSelect}
        />
      )}

      {/* Tabs */}
      <div className="glass w-fit max-w-full rounded-xl p-1.5">
        <TabBar
          tabs={TABS.map((t) => ({ id: t.id, label: t.label }))}
          activeTab={activeTab}
          onTabChange={(tabId) => setActiveTab(tabId as TabId)}
        />
      </div>

      {/* Tab panels */}
      <div>
        <div id="notes-panel" role="tabpanel" aria-labelledby="notes-panel-tab" hidden={activeTab !== "notes-panel"}>
          <NotesPanel projectId={project.id} onTagClick={handleTagClick} />
        </div>
        <div id="links-panel" role="tabpanel" aria-labelledby="links-panel-tab" hidden={activeTab !== "links-panel"}>
          <LinksPanel projectId={project.id} onTagClick={handleTagClick} />
        </div>
        <div id="websearch-panel" role="tabpanel" aria-labelledby="websearch-panel-tab" hidden={activeTab !== "websearch-panel"}>
          <WebSearchPanel projectId={project.id} />
        </div>
        <div id="roadmap-panel" role="tabpanel" aria-labelledby="roadmap-panel-tab" hidden={activeTab !== "roadmap-panel"}>
          <RoadmapPanel projectId={project.id} defaultSubject={project.name} />
        </div>
        <div id="tags-panel" role="tabpanel" aria-labelledby="tags-panel-tab" hidden={activeTab !== "tags-panel"}>
          <TagsPanel projectId={project.id} onTagClick={handleTagClick} />
        </div>
      </div>
    </div>
  );
}
