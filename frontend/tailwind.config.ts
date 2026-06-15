import type { Config } from 'tailwindcss'

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans:  ['DM Sans',       'system-ui', 'sans-serif'],
        serif: ['Source Serif 4','Georgia',   'serif'],
        mono:  ['DM Mono',       'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
