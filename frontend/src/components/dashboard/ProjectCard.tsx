import Link from "next/link";
import { format } from "date-fns";
import { ArrowRightIcon } from "@phosphor-icons/react";

interface ProjectCardProps {
  id: string;
  name: string;
  description?: string | null;
  createdAt: Date | string;
}

export function ProjectCard({ id, name, description, createdAt }: ProjectCardProps) {
  const initial = name.trim().charAt(0).toUpperCase() || "P";

  return (
    <Link
      href={`/projects/${id}`}
      className="group block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
    >
      <article className="sheet-soft h-full p-5 transition-all duration-200 ease-out group-hover:-translate-y-0.5 group-hover:shadow-elev-3 group-hover:border-accent/30">
        <div className="flex items-start justify-between gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 font-mono text-sm font-semibold text-accent transition-colors group-hover:bg-accent group-hover:text-accent-foreground">
            {initial}
          </span>
          <ArrowRightIcon
            size={16}
            weight="regular"
            aria-hidden="true"
            className="text-muted-foreground opacity-0 -translate-x-1 transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0"
          />
        </div>
        <h3 className="mt-4 font-semibold tracking-tight text-foreground truncate group-hover:text-accent transition-colors">
          {name}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground line-clamp-2 leading-relaxed">
          {description || "No description yet."}
        </p>
        <div className="mt-4 font-mono text-[11px] uppercase tracking-wider text-muted-foreground/80">
          Created {format(new Date(createdAt), "MMM d, yyyy")}
        </div>
      </article>
    </Link>
  );
}
