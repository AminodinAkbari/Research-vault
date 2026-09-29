"use client";

import { useState, FormEvent } from "react";
import { useToast } from "@/components/providers/ToastProvider";
import { useProjects } from "@/hooks/useProjects";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/types";

interface ProjectCreateFormProps {
  onSuccess?: () => void;
}

export function ProjectCreateForm({ onSuccess }: ProjectCreateFormProps) {
  const { success } = useToast();
  const { createProject, isCreating } = useProjects();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

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

    try {
      await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
      });

      success("Project created!");
      setName("");
      setDescription("");
      onSuccess?.();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setError(
          typeof err.body.detail === "string"
            ? err.body.detail
            : "Please check your input."
        );
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Session expired — please sign in again");
      } else {
        setError("Something went wrong. Please try again.");
      }
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
      <Button type="submit" isLoading={isCreating} className="w-full">
        Create
      </Button>
    </form>
  );
}