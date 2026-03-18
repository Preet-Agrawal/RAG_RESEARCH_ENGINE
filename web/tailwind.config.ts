import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        claude: {
          bg: '#171717',
          surface: '#212121',
          'surface-hover': '#2a2a2a',
          sidebar: '#171717',
          border: '#2e2e2e',
          'border-light': '#3a3a3a',
          text: '#ececec',
          'text-secondary': '#9b9b9b',
          'text-muted': '#6b6b6b',
          accent: '#c4976b',
          'accent-hover': '#d4a87b',
          'accent-soft': 'rgba(196, 151, 107, 0.12)',
          'user-msg': '#2b2b2b',
          'assistant-msg': '#212121',
          input: '#2f2f2f',
          'input-border': '#424242',
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
      },
      keyframes: {
        'pulse-dot': {
          '0%, 80%, 100%': { transform: 'scale(0.4)', opacity: '0.4' },
          '40%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
export default config
