"use client";

import { useProjects } from "@/hooks/useProjects";
import { ProjectCreateForm } from "@/components/forms/ProjectCreateForm";
import { ProjectCard } from "@/components/dashboard/ProjectCard";
import { EmptyState, LoadingSkeleton } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { PlusIcon } from "@phosphor-icons/react";

export default function DashboardPage() {
  const { projects, isLoading, isError } = useProjects();

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="space-y-3">
          <div className="h-8 w-52 animate-pulse rounded-md bg-muted" />
          <div className="h-4 w-72 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="sheet-soft p-5">
              <LoadingSkeleton lines={3} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-danger">Failed to load projects.</p>
        <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-3xl sm:text-4xl font-medium tracking-tight text-foreground">
          Your projects
        </h1>
        <p className="text-muted-foreground">
          Isolated containers for each research topic.
        </p>
      </div>

      <div className="sheet p-5 sm:p-6">
        <div className="mb-4 flex items-center gap-2 text-sm font-medium tracking-tight text-foreground">
          <PlusIcon size={16} weight="bold" aria-hidden="true" />
          New project
        </div>
        <ProjectCreateForm />
      </div>

      {projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Create your first project above to get started."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              id={project.id}
              name={project.name}
              description={project.description}
              createdAt={project.created_at}
            />
          ))}
        </div>
      )}
    </div>
  );
}
