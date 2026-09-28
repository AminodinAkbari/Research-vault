import { HTMLAttributes, forwardRef, ReactNode } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevation?: "none" | "sm" | "md";
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ elevation = "sm", className = "", children, ...props }, ref) => {
    const elevations = {
      none: "border border-border",
      sm: "border border-border shadow-sm",
      md: "border border-border shadow-md",
    };

    return (
      <div
        ref={ref}
        className={`rounded-lg bg-background ${elevations[elevation]} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title: ReactNode;
  description?: ReactNode;
}

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, description, className = "", ...props }, ref) => {
    return (
      <div ref={ref} className={`flex flex-col gap-1 p-4 ${className}`} {...props}>
        <div className="text-base font-semibold text-foreground">{title}</div>
        {description && (
          <div className="text-sm text-muted-foreground">{description}</div>
        )}
      </div>
    );
  }
);

CardHeader.displayName = "CardHeader";

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className = "", ...props }, ref) => {
    return (
      <div ref={ref} className={`p-4 pt-0 ${className}`} {...props} />
    );
  }
);

CardContent.displayName = "CardContent";
