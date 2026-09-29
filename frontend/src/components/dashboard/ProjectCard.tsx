import Link from "next/link";
import { format } from "date-fns";
import { Card } from "@/components/ui/Card";

interface ProjectCardProps {
  id: string;
  name: string;
  description?: string | null;
  createdAt: Date | string;
}

export function ProjectCard({ id, name, description, createdAt }: ProjectCardProps) {
  return (
    <Link
      href={`/projects/${id}`}
      className="block"
    >
      <Card elevation="sm" className="h-full hover:shadow-md transition-shadow">
        <div className="p-4">
          <h3 className="font-semibold text-foreground truncate">{name}</h3>
          <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
            {description || "No description yet."}
          </p>
          <div className="mt-3 text-xs text-muted-foreground">
            Created {format(new Date(createdAt), "MMM d, yyyy")}
          </div>
        </div>
      </Card>
    </Link>
  );
}