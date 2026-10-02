"use client";

import { KeyboardEvent, forwardRef } from "react";
import { motion, useReducedMotion } from "motion/react";

export interface Tab {
  id: string;
  label: string;
}

export interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  className?: string;
}

export const TabBar = forwardRef<HTMLDivElement, TabBarProps>(
  ({ tabs, activeTab, onTabChange, className = "" }, ref) => {
    const reduce = useReducedMotion();

    const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
      const currentIndex = tabs.findIndex((t) => t.id === activeTab);
      let newIndex: number;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        newIndex = (currentIndex + 1) % tabs.length;
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        newIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (e.key === "Home") {
        e.preventDefault();
        newIndex = 0;
      } else if (e.key === "End") {
        e.preventDefault();
        newIndex = tabs.length - 1;
      } else {
        return;
      }

      onTabChange(tabs[newIndex].id);
      document.getElementById(`${tabs[newIndex].id}-tab`)?.focus();
    };

    return (
      <div
        ref={ref}
        role="tablist"
        aria-label="Project sections"
        onKeyDown={handleKeyDown}
        className={`flex gap-1 overflow-x-auto rounded-lg bg-muted/60 p-1 ${className}`}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`${tab.id}-panel`}
              id={`${tab.id}-tab`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onTabChange(tab.id)}
              className={`relative whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium tracking-tight transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                isActive
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {isActive && (
                <motion.span
                  layoutId="tab-active-pill"
                  className="absolute inset-0 rounded-md bg-surface shadow-elev-1"
                  transition={
                    reduce
                      ? { duration: 0 }
                      : { type: "spring", stiffness: 500, damping: 40 }
                  }
                  aria-hidden="true"
                />
              )}
              <span className="relative z-10">{tab.label}</span>
            </button>
          );
        })}
      </div>
    );
  }
);

TabBar.displayName = "TabBar";
