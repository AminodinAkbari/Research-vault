"use client";

import { HTMLAttributes, forwardRef, ReactNode } from "react";
import { SquaresFour } from "@phosphor-icons/react";

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  action?: ReactNode;
}

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ title, description, action, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex flex-col items-center justify-center gap-3 py-16 text-center ${className}`}
        {...props}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/70 text-muted-foreground">
          <SquaresFour size={24} weight="regular" aria-hidden="true" />
        </div>
        <div className="text-base font-medium tracking-tight text-foreground">{title}</div>
        {description && (
          <div className="text-sm text-muted-foreground max-w-sm leading-relaxed">
            {description}
          </div>
        )}
        {action && <div className="mt-3">{action}</div>}
      </div>
    );
  }
);

EmptyState.displayName = "EmptyState";

export interface LoadingSkeletonProps extends HTMLAttributes<HTMLDivElement> {
  lines?: number;
  avatar?: boolean;
}

export const LoadingSkeleton = forwardRef<HTMLDivElement, LoadingSkeletonProps>(
  ({ lines = 3, avatar = false, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        role="status"
        aria-label="Loading"
        className={`flex flex-col gap-3 ${className}`}
        {...props}
      >
        <span className="sr-only">Loading...</span>
        {avatar && (
          <div className="h-10 w-10 rounded-full bg-muted animate-pulse" />
        )}
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-4 bg-muted rounded animate-pulse"
            style={{ width: `${100 - i * 15}%` }}
          />
        ))}
      </div>
    );
  }
);

LoadingSkeleton.displayName = "LoadingSkeleton";
