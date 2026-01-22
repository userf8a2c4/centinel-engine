import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        "centinel-blue": "#00D4FF",
        "centinel-purple": "#8B5CF6",
        "centinel-green": "#10B981",
        "centinel-bg": "#0B0F1A"
      },
      boxShadow: {
        glow: "0 0 30px rgba(0, 212, 255, 0.35)",
        "glow-purple": "0 0 30px rgba(139, 92, 246, 0.35)"
      }
    }
  },
  plugins: []
};

export default config;
