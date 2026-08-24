/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,vue}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        bg: {
          base: '#0A0A0F',
          card: '#13131A',
          elevate: '#1A1A24',
          hover: '#22222E',
        },
        accent: {
          cyan: '#00D9FF',
          violet: '#9D4EDD',
          pink: '#FF2E97',
        },
        text: {
          primary: '#FAFAFA',
          secondary: '#9CA3AF',
          muted: '#6B7280',
        },
        border: {
          subtle: '#2A2A38',
          DEFAULT: '#3A3A4A',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', '"Sora"', 'system-ui', 'sans-serif'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      backgroundImage: {
        'grid-pattern':
          'linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)',
        'radial-glow':
          'radial-gradient(circle at center, rgba(0,217,255,0.15) 0%, transparent 60%)',
        'gradient-cv':
          'linear-gradient(135deg, #00D9FF 0%, #9D4EDD 100%)',
      },
      backgroundSize: {
        'grid-lg': '64px 64px',
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'gradient-shift': 'gradientShift 8s ease infinite',
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
        pulseGlow: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
    },
  },
  plugins: [],
};
