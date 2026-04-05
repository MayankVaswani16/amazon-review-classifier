/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // SentimentIQ Obsidian Design System
        surface: {
          DEFAULT: '#131318',
          dim: '#131318',
          bright: '#39393e',
          container: '#1f1f24',
          'container-high': '#2a292f',
          'container-highest': '#35343a',
          'container-low': '#1b1b20',
          'container-lowest': '#0e0e13',
        },
        primary: {
          DEFAULT: '#6366f1',
          50: '#e1e0ff',
          100: '#c0c1ff',
          200: '#a5a7ff',
          300: '#8083ff',
          400: '#818cf8',
          500: '#6366f1',
          600: '#494bd6',
          700: '#3730a3',
          800: '#2f2ebe',
          900: '#1000a9',
        },
        accent: {
          50: '#fdf4ff',
          100: '#fae8ff',
          200: '#f5d0fe',
          300: '#f0abfc',
          400: '#e879f9',
          500: '#d946ef',
          600: '#c026d3',
          700: '#a21caf',
          800: '#86198f',
          900: '#701a75',
        },
        dark: {
          50: '#e4e1e9',
          100: '#c7c4d7',
          200: '#908fa0',
          300: '#c7c4d7',
          400: '#908fa0',
          500: '#64748b',
          600: '#464554',
          700: '#35343a',
          800: '#1e293b',
          900: '#131318',
          950: '#0e0e13',
        },
        sentiment: {
          positive: '#4edea3',
          'positive-bg': '#00a572',
          negative: '#ffb4ab',
          'negative-bg': '#93000a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      boxShadow: {
        'ambient': '0 20px 40px rgba(99, 102, 241, 0.08)',
        'ambient-lg': '0 25px 50px rgba(99, 102, 241, 0.12)',
        'glow': '0 0 20px rgba(99, 102, 241, 0.15)',
      },
    },
  },
  plugins: [],
}
