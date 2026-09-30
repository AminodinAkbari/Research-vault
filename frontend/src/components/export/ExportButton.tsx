import { endpoints } from "@/lib/endpoints";

export interface ExportButtonProps {
  projectId: string;
}

/**
 * A24: GET /projects/{id}/export/markdown accepts the httpOnly cookie, so a
 * plain anchor with `download` fetches the file in one click (US6 scenario 4).
 */
export function ExportButton({ projectId }: ExportButtonProps) {
  return (
    <div className="flex justify-end">
      <a
        href={endpoints.exportMarkdown(projectId)}
        download
        className="inline-flex h-10 items-center rounded border border-border bg-background px-4 text-sm font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        Export as Markdown
      </a>
    </div>
  );
}
