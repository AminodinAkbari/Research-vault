import { DownloadSimpleIcon } from "@phosphor-icons/react";
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
        className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-medium tracking-tight text-foreground shadow-elev-1 transition-all duration-150 hover:bg-muted hover:border-foreground/20 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <DownloadSimpleIcon size={16} weight="regular" aria-hidden="true" />
        Export as Markdown
      </a>
    </div>
  );
}
