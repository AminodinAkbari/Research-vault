"use client";

import { useProjects } from "@/hooks/useProjects";
import { ProjectCreateForm } from "@/components/forms/ProjectCreateForm";
import { ProjectCard } from "@/components/dashboard/ProjectCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

export default function DashboardPage() {
  const { projects, isLoading, isError, createProject, isCreating } = useProjects();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground">Loading projects...</p>
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Your projects</h1>
        <p className="text-muted-foreground mt-1">
          Isolated containers for each research topic.
        </p>
      </div>

      <ProjectCreateForm />

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