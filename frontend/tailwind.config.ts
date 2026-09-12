import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // 广汽集团品牌配色体系（Sprint 7）
        gac: {
          primary: '#003C8F',         // 广汽蓝（主色）
          'primary-light': '#0050B8', // 浅蓝（hover）
          'primary-dark': '#002855',  // 深蓝（按下）
          accent: '#C8102E',          // 广汽红（强调）
          gold: '#FFB81C',            // 金色（高亮）
          'gray-50': '#F8FAFC',
          'gray-100': '#F1F5F9',
          'gray-200': '#E2E8F0',
          'gray-300': '#CBD5E1',
          'gray-500': '#64748B',
          'gray-700': '#334155',
          'gray-900': '#0F172A',
        },
        // 兼容旧版
        'gac-brand': {
          green: '#10B981',
          red: '#DC2626',
          blue: '#003C8F',
          dark: '#1F2937',
          gray: '#6B7280',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'PingFang SC',
          'Microsoft YaHei',
          'Inter',
          'system-ui',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0, 60, 143, 0.5)' },
          '50%': { boxShadow: '0 0 20px rgba(0, 60, 143, 0.8)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
