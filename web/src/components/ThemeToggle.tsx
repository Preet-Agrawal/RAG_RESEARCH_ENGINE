'use client';

import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

type Theme = 'light' | 'dark';

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  // Read the current theme from <html> on mount (set by inline script in layout.tsx)
  useEffect(() => {
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'dark' : 'light');
  }, []);

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    if (next === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try {
      localStorage.setItem('theme', next);
    } catch {}
  };

  // Don't render until we've read the initial theme (avoids SSR mismatch)
  if (theme === null) {
    return (
      <button
        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-claude-text-secondary text-sm"
        aria-label="Loading theme"
      >
        <div className="w-4 h-4" />
        <span className="opacity-0">Theme</span>
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-claude-surface-hover text-claude-text-secondary hover:text-claude-text transition-colors text-sm"
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? (
        <Sun className="w-4 h-4 text-amber-400" />
      ) : (
        <Moon className="w-4 h-4 text-indigo-500" />
      )}
      {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
    </button>
  );
}
