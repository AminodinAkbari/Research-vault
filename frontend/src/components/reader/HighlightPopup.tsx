"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, useReducedMotion } from "motion/react";
import { XIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { HIGHLIGHT_COLOR_HEX, HIGHLIGHT_COLOR_NAMES } from "@/lib/constants";

export interface HighlightSelection {
  text: string;
  startOffset: number;
  endOffset: number;
  range: Range;
  rect: { top: number; left: number; bottom: number };
}

export interface HighlightSavePayload {
  annotation: string;
  color: string;
}

export interface HighlightPopupProps {
  selection: HighlightSelection;
  onSave: (payload: HighlightSavePayload) => Promise<void>;
  onClose: () => void;
}

const SAVE_ERROR = "Failed to save highlight. Please try again.";

export function HighlightPopup({
  selection,
  onSave,
  onClose,
}: HighlightPopupProps) {
  const popupRef = useRef<HTMLFormElement>(null);
  const [annotation, setAnnotation] = useState("");
  const [color, setColor] = useState<string>("yellow");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const reduce = useReducedMotion();

  // FR-023: dismiss on outside click (and Escape, for keyboard users)
  useEffect(() => {
    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (popupRef.current && target && !popupRef.current.contains(target)) {
        onClose();
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  const submit = async (chosenColor: string) => {
    if (isSaving) return;
    setError("");
    setIsSaving(true);
    try {
      await onSave({ annotation: annotation.trim(), color: chosenColor });
    } catch {
      // Keep the popup open with the input intact (US5 scenario 6)
      setError(SAVE_ERROR);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void submit(color);
  };

  // A swatch click selects the color and submits immediately
  const handleSwatch = (name: string) => {
    setColor(name);
    void submit(name);
  };

  if (typeof document === "undefined") return null;

  const position = {
    position: "absolute" as const,
    top: selection.rect.bottom + window.scrollY + 8,
    left: selection.rect.left + window.scrollX,
    zIndex: 1000,
    transformOrigin: "top left",
  };

  return createPortal(
    <motion.form
      id="highlight-popup"
      ref={popupRef}
      aria-label="Save highlight"
      onSubmit={handleSubmit}
      style={position}
      initial={reduce ? false : { opacity: 0, y: -6, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 480, damping: 32, mass: 0.7 }}
      className="glass w-72 rounded-xl p-3.5"
      noValidate
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium tracking-tight text-foreground">
          Highlight selection
        </span>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          disabled={isSaving}
          className="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 transition-colors"
        >
          <XIcon size={14} weight="bold" aria-hidden="true" />
        </button>
      </div>

      <div className="mt-3">
        <Input
          label="Note (optional)"
          name="annotation"
          autoComplete="off"
          maxLength={2000}
          autoFocus
          value={annotation}
          onChange={(event) => setAnnotation(event.target.value)}
          disabled={isSaving}
        />
      </div>

      <div className="mt-4 flex items-center gap-2">
        <div
          role="group"
          aria-label="Highlight color"
          className="flex items-center gap-1.5"
        >
          {HIGHLIGHT_COLOR_NAMES.map((name, index) => (
            <motion.button
              key={name}
              type="button"
              data-color={name}
              data-testid="highlight-swatch"
              title={name}
              aria-label={`Highlight in ${name}`}
              aria-pressed={color === name}
              disabled={isSaving}
              onClick={() => handleSwatch(name)}
              style={{ backgroundColor: HIGHLIGHT_COLOR_HEX[name] }}
              initial={reduce ? false : { opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 520,
                damping: 30,
                delay: reduce ? 0 : 0.06 + index * 0.03,
              }}
              whileHover={reduce ? undefined : { scale: 1.15 }}
              whileTap={{ scale: 0.9 }}
              className={`h-6 w-6 rounded-pill border border-border/60 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50 ${
                color === name ? "ring-2 ring-accent ring-offset-2" : ""
              }`}
            />
          ))}
        </div>
        <Button
          type="submit"
          size="sm"
          className="ml-auto"
          isLoading={isSaving}
        >
          Save
        </Button>
      </div>

      {error && (
        <p role="alert" className="mt-2.5 text-sm text-danger">
          {error}
        </p>
      )}
    </motion.form>,
    document.body
  );
}
