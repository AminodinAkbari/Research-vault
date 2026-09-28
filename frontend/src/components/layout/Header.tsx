"use client";

import Link from "next/link";
import { LogoutButton } from "./LogoutButton";

export function Header() {
  return (
    <header className="border-b border-border bg-background">
      <div className="container mx-auto px-4 py-4 max-w-6xl flex items-center justify-between">
        <Link
          href="/dashboard"
          className="text-lg font-bold text-foreground hover:text-accent transition-colors"
        >
          Research Vault
        </Link>
        <nav aria-label="Primary">
          <ul className="flex items-center gap-4 list-none m-0 p-0">
            <li>
              <LogoutButton />
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
