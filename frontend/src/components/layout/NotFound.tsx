import Link from "next/link";
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
    <div className="min-h-[400px] flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-3xl font-bold text-foreground mb-2">{title}</h1>
      <p className="text-muted-foreground max-w-md mb-6">{message}</p>
      <Link href={actionHref}>
        <Button variant="primary">{actionLabel}</Button>
      </Link>
    </div>
  );
}