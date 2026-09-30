import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ONE neutral temperature: zinc
        background: "var(--background)",
        foreground: "var(--foreground)",
        // ONE accent (locked app-wide). `accent` = text/links/ring,
        // `accent.solid` = filled surfaces (buttons, toasts).
        accent: {
          DEFAULT: "rgb(var(--accent-rgb) / <alpha-value>)",
          hover: "var(--accent-hover)",
          foreground: "var(--accent-foreground)",
          solid: "var(--accent-solid)",
          "solid-hover": "var(--accent-solid-hover)",
        },
        // Status colors (exempt from accent lock)
        success: "var(--success)",
        warning: "var(--warning)",
        danger: {
          DEFAULT: "rgb(var(--danger-rgb) / <alpha-value>)",
          solid: "var(--danger-solid)",
          "solid-hover": "var(--danger-solid-hover)",
        },
        // Muted surfaces
        muted: {
          DEFAULT: "rgb(var(--muted-rgb) / <alpha-value>)",
          foreground: "var(--muted-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        // Focus ring uses the accent so `ring-ring` is never a dead class
        ring: "rgb(var(--accent-rgb) / <alpha-value>)",
      },
      ringOffsetColor: {
        DEFAULT: "var(--background)",
      },
      borderRadius: {
        // ONE radius token: 8-10px
        DEFAULT: "var(--radius)",
        sm: "calc(var(--radius) - 2px)",
        lg: "var(--radius)",
        xl: "calc(var(--radius) + 4px)",
        // Pill exception: tag chips/status badges
        pill: "9999px",
      },
      spacing: {
        // 4px base scale
        "1": "4px",
        "2": "8px",
        "3": "12px",
        "4": "16px",
        "5": "20px",
        "6": "24px",
        "7": "28px",
        "8": "32px",
        "10": "40px",
        "12": "48px",
        "16": "64px",
        "20": "80px",
        "24": "96px",
      },
    },
  },
  plugins: [],
};

export default config;
