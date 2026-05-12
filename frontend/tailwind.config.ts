import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./data/**/*.{js,ts,jsx,tsx,mdx}",
    "./App.tsx",
  ],
  theme: {
    extend: {
      colors: {
        app: "#0A0A0A",
        sidebar: "#111111",
        elevated: "#171717",
        hover: "#1F1F1F",
        line: "rgba(255,255,255,0.06)",
        primary: "#F5F5F5",
        secondary: "#A3A3A3",
        muted: "#737373",
        accent: {
          DEFAULT: "#E0B15B",
          hover: "#F0C46A",
        },
        ready: "#4ADE80",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      boxShadow: {
        paper:
          "inset 0 0 0 1px rgba(10,10,10,0.08), 0 10px 22px rgba(0,0,0,0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
