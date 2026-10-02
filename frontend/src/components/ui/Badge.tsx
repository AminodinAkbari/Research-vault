import { HTMLAttributes, forwardRef } from "react";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "danger" | "note" | "link";
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = "default", className = "", children, ...props }, ref) => {
    const variants = {
      default: "bg-muted text-muted-foreground border border-border",
      success: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
      warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
      danger: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
      note: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
      link: "bg-muted text-foreground border border-border",
    };

    return (
      <span
        ref={ref}
        className={`inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium tracking-tight ${variants[variant]} ${className}`}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";

export interface TagChipProps extends HTMLAttributes<HTMLSpanElement> {
  onRemove?: () => void;
}

export const TagChip = forwardRef<HTMLSpanElement, TagChipProps>(
  ({ onRemove, className = "", children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={`inline-flex items-center gap-1 rounded-pill bg-muted px-2.5 py-1 text-xs font-medium text-foreground border border-border transition-colors hover:border-foreground/20 ${className}`}
        {...props}
      >
        {children}
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="ml-0.5 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Remove tag"
          >
            ×
          </button>
        )}
      </span>
    );
  }
);

TagChip.displayName = "TagChip";

export const TAG_CHIP_CLASS =
  "inline-flex items-center gap-1 rounded-pill border border-border bg-muted px-2.5 py-1 text-xs font-medium text-foreground";

export interface TagFilterChipProps {
  tag: { id: string; name: string };
  onSelect?: (tag: { id: string; name: string }) => void;
}

export function TagFilterChip({ tag, onSelect }: TagFilterChipProps) {
  if (!onSelect) return <Badge>{tag.name}</Badge>;

  return (
    <button
      type="button"
      onClick={() => onSelect(tag)}
      className={`${TAG_CHIP_CLASS} transition-all duration-150 hover:bg-accent/10 hover:border-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.97]`}
    >
      {tag.name}
    </button>
  );
}
