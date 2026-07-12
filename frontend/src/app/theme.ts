import { useEffect, useState } from "react";

export const THEME_STORAGE_KEY = "course_nexus_theme";

type ThemeMode = "dark" | "light";

function readStoredTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  return localStorage.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
}

function applyTheme(theme: ThemeMode) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-course-nexus-theme", theme);
  }
}

export function useCourseNexusTheme() {
  const [theme, setTheme] = useState<ThemeMode>(readStoredTheme);

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  return {
    isDarkMode: theme === "dark",
    theme,
    toggleTheme,
  };
}
