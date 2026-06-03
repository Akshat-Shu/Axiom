import { createContext, useContext } from "react";

export const themes = {
  dark: {
    bg: "#0f0f11",
    surface: "#16161a",
    surfaceAlt: "#23232a",
    border: "#2a2a30",
    text: "#e8e8ec",
    textMuted: "#888",
    textDim: "#555",
    accent: "#6366f1",
    accentHover: "#818cf8",
    danger: "#ef4444",
    success: "#22c55e",
    warning: "#f97316",
    badge: {
      flexible: { bg: "#0c2233", color: "#38bdf8" },
      pending:  { bg: "#1a1a2e", color: "#818cf8" },
      accepted: { bg: "#122212", color: "#22c55e" },
      declined: { bg: "#2e1a1a", color: "#ef4444" },
    },
  },
  light: {
    bg: "#f4f4f6",
    surface: "#ffffff",
    surfaceAlt: "#ededf3",
    border: "#dddde8",
    text: "#111118",
    textMuted: "#555",
    textDim: "#999",
    accent: "#4f46e5",
    accentHover: "#6366f1",
    danger: "#dc2626",
    success: "#16a34a",
    warning: "#ea580c",
    badge: {
      flexible: { bg: "#e0f2fe", color: "#0369a1" },
      pending:  { bg: "#ede9fe", color: "#4f46e5" },
      accepted: { bg: "#dcfce7", color: "#15803d" },
      declined: { bg: "#fee2e2", color: "#b91c1c" },
    },
  },
};

export const ThemeContext = createContext({ theme: themes.dark, isDark: true, toggle: () => {} });
export const useTheme = () => useContext(ThemeContext);
