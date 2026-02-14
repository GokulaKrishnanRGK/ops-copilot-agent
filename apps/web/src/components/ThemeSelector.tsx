import { ThemeMode } from "../types";

type ThemeSelectorProps = {
  value: ThemeMode;
  onChange: (value: ThemeMode) => void;
};

export function ThemeSelector({ value, onChange }: ThemeSelectorProps) {
  return (
    <label className="theme-switcher">
      Theme
      <select value={value} onChange={(event) => onChange(event.target.value as ThemeMode)}>
        <option value="system">System</option>
        <option value="dark">Dark</option>
        <option value="light">Light</option>
      </select>
    </label>
  );
}
