import Link from "next/link";
import { XCircle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/Button";

interface NotFoundProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  actionHref?: string;
}

export function NotFound({
  title = "Not found",
  message = "The resource you're looking for doesn't exist or you don't have access to it.",
  actionLabel = "Back to dashboard",
  actionHref = "/dashboard",
}: NotFoundProps) {
  return (
    <div className="min-h-[400px] flex flex-col items-center justify-center text-center px-4 py-16">
      <div className="sheet max-w-md w-full p-8 sm:p-10">
        <div className="mx-auto mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          <XCircle size={22} weight="regular" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground mb-2">{title}</h1>
        <p className="text-muted-foreground max-w-sm mx-auto mb-6 text-sm leading-relaxed">{message}</p>
        <Link href={actionHref} className="inline-block">
          <Button variant="primary">{actionLabel}</Button>
        </Link>
      </div>
    </div>
  );
}
