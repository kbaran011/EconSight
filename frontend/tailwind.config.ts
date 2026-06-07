import type { Config } from 'tailwindcss'

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          600: '#1d4ed8',
          700: '#1e40af',
          900: '#1e3a5f',
        },
        surface: '#f8fafc',
      },
    },
  },
  plugins: [],
} satisfies Config
