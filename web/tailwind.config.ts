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
          bg: '#1C1C1E',
          surface: '#2C2C2E',
          border: '#3A3A3C',
          text: '#F5F5F7',
          'text-secondary': '#A8A8AC',
          accent: '#CD7F32',
          'accent-hover': '#E09A52',
        },
      },
    },
  },
  plugins: [],
}
export default config
