"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/providers/ToastProvider";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

interface ProjectCreateFormProps {
  onSuccess?: () => void;
}

export function ProjectCreateForm({ onSuccess }: ProjectCreateFormProps) {
  const router = useRouter();
  const { success } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }
    if (name.length > 200) {
      setError("Project name must be 200 characters or less.");
      return;
    }
    if (description.length > 2000) {
      setError("Description must be 2000 characters or less.");
      return;
    }

    setIsLoading(true);
    try {
      const { createProject } = await import("@/hooks/useProjects");
      // We need to access the hook differently - let's use a direct API call
      const { apiFetch } = await import("@/lib/api");
      const { endpoints } = await import("@/lib/endpoints");
      const { ProjectRead, ProjectCreate } = await import("@/lib/types");

      const newProject = await apiFetch(endpoints.projects, ProjectRead, {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), description: description.trim() || undefined }),
      });

      success("Project created!");
      setName("");
      setDescription("");
      onSuccess?.();
      router.push(`/projects/${newProject.id}`);
    } catch (err: any) {
      if (err.status === 422) {
        setError(err.body?.detail || "Please check your input.");
      } else if (err.status === 401) {
        setError("Session expired — please sign in again");
        router.push("/login");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <Input
        label="Project name"
        name="name"
        required
        maxLength={200}
        placeholder="Project name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={error}
      />
      <Input
        label="Description (optional)"
        name="description"
        maxLength={2000}
        placeholder="Description (optional)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <Button type="submit" isLoading={isLoading} className="w-full">
        Create
      </Button>
    </form>
  );
}