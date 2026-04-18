import { ThemeMode } from "../types";

type ThemeSelectorProps = {
  value: ThemeMode;
  onChange: (value: ThemeMode) => void;
};

export function ThemeSelector({ value, onChange }: ThemeSelectorProps) {
  const isDark = value !== "light";

  function toggle() {
    onChange(isDark ? "light" : "dark");
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className={`theme-toggle ${isDark ? "dark" : "light"}`}
      onClick={toggle}
    >
      <span className="theme-track">
        <span className="theme-thumb" />
        <span className="theme-slot theme-slot-sun" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2.5" />
            <path d="M12 19.5V22" />
            <path d="M4.93 4.93l1.77 1.77" />
            <path d="M17.3 17.3l1.77 1.77" />
            <path d="M2 12h2.5" />
            <path d="M19.5 12H22" />
            <path d="M4.93 19.07l1.77-1.77" />
            <path d="M17.3 6.7l1.77-1.77" />
          </svg>
        </span>
        <span className="theme-slot theme-slot-moon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
          </svg>
        </span>
      </span>
    </button>
  );
}
