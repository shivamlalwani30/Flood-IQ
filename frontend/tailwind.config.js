/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#020B14',
          secondary: '#071520',
          panel: '#0A1E2E',
          card: '#0D2438',
          hover: '#102840',
        },
        accent: {
          cyan: '#00F5FF',
          teal: '#00D4AA',
          blue: '#0EA5E9',
          amber: '#F59E0B',
          red: '#FF3B5C',
          green: '#00FF87',
        },
        text: {
          primary: '#E8F4F8',
          secondary: '#7BAABD',
          dim: '#3D6678',
          muted: '#1E4A5E',
        },
        border: {
          primary: '#0F2D42',
          accent: '#1A4A63',
          glow: '#00F5FF20',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ripple': 'ripple 1.8s ease-out infinite',
        'flood-pulse': 'flood-pulse 2s ease-in-out infinite',
        'dot-pulse': 'dot-pulse 1.5s ease-in-out infinite',
        'count-up': 'count-up 0.3s ease-out',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        ripple: {
          '0%': { transform: 'scale(0.95)', opacity: '0.7' },
          '70%': { transform: 'scale(1.4)', opacity: '0' },
          '100%': { transform: 'scale(1.4)', opacity: '0' },
        },
        'flood-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        'dot-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0, 245, 255, 0.7)' },
          '50%': { boxShadow: '0 0 0 6px rgba(0, 245, 255, 0)' },
        },
        'count-up': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
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
