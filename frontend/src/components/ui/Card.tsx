import { HTMLAttributes, forwardRef, ReactNode } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevation?: "none" | "sm" | "md";
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ elevation = "sm", className = "", children, ...props }, ref) => {
    const elevations = {
      none: "border border-border bg-surface",
      sm: "sheet-soft",
      md: "sheet",
    };

    return (
      <div
        ref={ref}
        className={`${elevations[elevation]} transition-all duration-200 ease-out ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export interface CardHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title: ReactNode;
  description?: ReactNode;
}

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, description, className = "", ...props }, ref) => {
    return (
      <div ref={ref} className={`flex flex-col gap-1 p-5 ${className}`} {...props}>
        <div className="text-base font-semibold tracking-tight text-foreground">{title}</div>
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
    return <div ref={ref} className={`p-5 pt-0 ${className}`} {...props} />;
  }
);

CardContent.displayName = "CardContent";
