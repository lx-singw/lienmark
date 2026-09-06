/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'cinema-black': '#050811',
        'cinema-navy': '#090e1a',
        'cinema-slate': '#0f172a',
        'cinema-card': 'rgba(15, 23, 42, 0.75)',
        'gold-accent': '#f59e0b',
        'cyan-accent': '#38bdf8',
        'emerald-accent': '#10b981',
        'crimson-accent': '#ef4444',
      },
      keyframes: {
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'glow-border': {
          '0%, 100%': {
            borderColor: 'rgba(56, 189, 248, 0.3)',
            boxShadow: '0 0 15px rgba(56, 189, 248, 0.15)',
          },
          '50%': {
            borderColor: 'rgba(56, 189, 248, 0.8)',
            boxShadow: '0 0 25px rgba(56, 189, 248, 0.4)',
          },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'radar-sweep': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'pulse-slow': 'pulse-slow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-border': 'glow-border 2.5s ease-in-out infinite',
        'shimmer': 'shimmer 2.5s linear infinite',
        'radar-sweep': 'radar-sweep 4s linear infinite',
      },
    },
  },
  plugins: [],
};
