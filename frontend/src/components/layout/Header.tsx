"use client";

import Link from "next/link";
import { HighlighterCircleIcon, MoonIcon, SunIcon } from "@phosphor-icons/react";
import { LogoutButton } from "./LogoutButton";
import { useTheme } from "@/components/providers/ThemeProvider";

export function Header() {
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/70 bg-background/75 backdrop-blur-xl backdrop-saturate-150">
      <div className="app-wrap flex h-16 items-center justify-between">
        <Link
          href="/dashboard"
          className="group flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-accent-foreground shadow-sm transition-transform duration-200 group-hover:scale-105">
            <HighlighterCircleIcon size={18} weight="fill" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-foreground group-hover:text-accent transition-colors">
            Research Vault
          </span>
        </Link>
        <nav aria-label="Primary">
          <ul className="flex items-center gap-2 list-none m-0 p-0">
            <li>
              <button
                type="button"
                aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-all duration-150 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-95"
              >
                {theme === "dark" ? (
                  <SunIcon size={17} weight="regular" />
                ) : (
                  <MoonIcon size={17} weight="regular" />
                )}
              </button>
            </li>
            <li>
              <LogoutButton />
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
