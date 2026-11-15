import { ComponentProps } from "react";
import { IconContext } from "@phosphor-icons/react";

export interface IconProps extends ComponentProps<"span"> {
  size?: number;
  weight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
}

export function Icon({
  size = 20,
  weight = "regular",
  className = "",
  children,
  ...props
}: IconProps) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex ${className}`}
      {...props}
    >
      <IconContext.Provider value={{ size, weight, color: "currentColor" }}>
        {children}
      </IconContext.Provider>
    </span>
  );
}
