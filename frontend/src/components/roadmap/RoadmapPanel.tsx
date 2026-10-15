"use client";

import { useState, FormEvent } from "react";
import { MapTrifoldIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, LoadingSkeleton } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { useRoadmap } from "@/hooks/useRoadmap";
import { useNotes } from "@/hooks/useNotes";
import { useToast } from "@/components/providers/ToastProvider";
import { ApiError, RoadmapStep } from "@/lib/types";

export interface RoadmapPanelProps {
  projectId: string;
  /** Optional default subject, e.g. the project name. */
  defaultSubject?: string;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.body.detail === "string"
      ? error.body.detail
      : "The request was rejected. Check the topic and try again.";
  }
  return "The AI service is currently unavailable. Please try again later.";
}

function noteContentForStep(step: RoadmapStep): string {
  const keywords =
    step.keywords.length > 0
      ? `\n\nKey subtopics:\n${step.keywords.map((k) => `- ${k}`).join("\n")}`
      : "";
  return `${step.step}${keywords}`;
}

export function RoadmapPanel({ projectId, defaultSubject = "" }: RoadmapPanelProps) {
  const { roadmap, generateRoadmap, isGenerating, isError, error, reset } =
    useRoadmap();
  const { createNote } = useNotes(projectId);
  const { success, error: showError } = useToast();

  const [subject, setSubject] = useState(defaultSubject);
  const [savingStep, setSavingStep] = useState<number | null>(null);
  const [savedSteps, setSavedSteps] = useState<Set<number>>(new Set());

  const hasRoadmap = roadmap.length > 0;

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = subject.trim();
    if (!trimmed || isGenerating) return;
    try {
      await generateRoadmap({ subject: trimmed });
    } catch {
      // surfaced below via isError/error
    }
  };

  const handleSaveToNotes = async (index: number) => {
    const step = roadmap[index];
    if (!step) return;
    setSavingStep(index);
    try {
      await createNote({
        title: step.step.slice(0, 200),
        content: noteContentForStep(step),
      });
      setSavedSteps((prev) => new Set(prev).add(index));
      success("Roadmap step saved to notes");
    } catch (err) {
      showError(errorMessage(err));
    } finally {
      setSavingStep(null);
    }
  };

  const subjectForm = (
    <form onSubmit={handleGenerate} className="flex flex-col gap-2 sm:flex-row">
      <label htmlFor="roadmap-subject" className="sr-only">
        Research topic
      </label>
      <input
        id="roadmap-subject"
        type="text"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        maxLength={200}
        placeholder="Research topic, e.g. “Retrieval-augmented generation”"
        className="h-10 w-full min-w-0 flex-1 rounded border border-border bg-surface px-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:max-w-sm"
      />
      <Button
        type="submit"
        isLoading={isGenerating}
        disabled={!subject.trim()}
        leftIcon={<Icon size={16}><MapTrifoldIcon weight="bold" /></Icon>}
      >
        {hasRoadmap ? "Regenerate Roadmap" : "Generate Research Roadmap"}
      </Button>
    </form>
  );

  // Empty state — nothing generated yet
  if (!hasRoadmap) {
    return (
      <div className="space-y-4">
        <EmptyState
          title="No roadmap yet"
          description="Describe the research topic and the AI will draft a step-by-step roadmap you can save into your notes."
          action={
            <div className="flex flex-col items-center gap-3">
              {subjectForm}
              {isError && (
                <p role="alert" className="max-w-sm text-sm text-danger">
                  {errorMessage(error)}
                </p>
              )}
            </div>
          }
        />
      </div>
    );
  }

  // Loading state — keep the layout while a (re)generation runs
  if (isGenerating) {
    return (
      <div className="space-y-4" role="status" aria-busy="true">
        <p className="text-sm text-muted-foreground">
          Generating roadmap…
        </p>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-4">
              <div className="h-9 w-9 shrink-0 rounded-full bg-muted animate-pulse" />
              <Card elevation="sm" className="flex-1 p-4">
                <LoadingSkeleton lines={2} />
              </Card>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Timeline view
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">{subjectForm}</div>
        <Button variant="ghost" size="sm" onClick={reset}>
          Clear
        </Button>
      </div>

      {isError && (
        <p role="alert" className="text-sm text-danger">
          {errorMessage(error)}
        </p>
      )}

      <ol className="relative space-y-4 border-l border-border pl-6 ml-4">
        {roadmap.map((step, index) => {
          const isSaved = savedSteps.has(index);
          return (
            <li key={index} className="relative">
              <span
                aria-hidden="true"
                className="absolute -left-[33px] flex h-7 w-7 items-center justify-center rounded-full bg-accent-solid text-[11px] font-semibold tabular-nums text-accent-foreground"
              >
                {index + 1}
              </span>
              <Card elevation="sm" className="p-4 sm:p-5">
                <div className="flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-reading text-base font-semibold leading-snug text-foreground">
                      {step.step}
                    </h3>
                    <Button
                      variant={isSaved ? "secondary" : "outline"}
                      size="sm"
                      isLoading={savingStep === index}
                      disabled={isSaved || savingStep !== null}
                      onClick={() => handleSaveToNotes(index)}
                      className="shrink-0"
                    >
                      {isSaved ? "Saved ✓" : "Save to Notes"}
                    </Button>
                  </div>
                  {step.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {step.keywords.map((keyword) => (
                        <Badge key={keyword} variant="note">
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
