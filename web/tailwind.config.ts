import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        claude: {
          // All claude-* colors map to CSS variables in globals.css
          // Values swap automatically when `.dark` is toggled on <html>
          bg: 'var(--claude-bg)',
          surface: 'var(--claude-surface)',
          'surface-hover': 'var(--claude-surface-hover)',
          sidebar: 'var(--claude-sidebar)',
          border: 'var(--claude-border)',
          'border-light': 'var(--claude-border-light)',
          text: 'var(--claude-text)',
          'text-secondary': 'var(--claude-text-secondary)',
          'text-muted': 'var(--claude-text-muted)',
          accent: 'var(--claude-accent)',
          'accent-hover': 'var(--claude-accent-hover)',
          'accent-soft': 'var(--claude-accent-soft)',
          'user-msg': 'var(--claude-user-msg)',
          'assistant-msg': 'var(--claude-assistant-msg)',
          input: 'var(--claude-input)',
          'input-border': 'var(--claude-input-border)',
        },
      },
      maxWidth: {
        chat: '48rem',
      },
      fontSize: {
        'chat': ['0.9375rem', '1.75rem'],
      },
      animation: {
        'pulse-dot': 'pulse-dot 1.4s infinite ease-in-out both',
        shimmer: 'shimmer 1.5s infinite',
      },
      keyframes: {
        'pulse-dot': {
          '0%, 80%, 100%': { transform: 'scale(0.4)', opacity: '0.4' },
          '40%': { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
export default config
