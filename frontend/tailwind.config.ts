import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // 广汽品牌配色体系
        "gac-brand": {
          green: "#10B981",   // 埃安绿
          red: "#DC2626",     // 广汽红
          blue: "#2563EB",    // 科技蓝
          dark: "#1F2937",    // 深灰背景
          gray: "#6B7280",    // 中灰文字
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 5px rgba(16, 185, 129, 0.5)" },
          "50%": { boxShadow: "0 0 20px rgba(16, 185, 129, 0.8)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
