/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        sova: {
          bg: "#0A0E12",
          panel: "#12171C",
          panel2: "#192127",
          border: "#26323A",
          accent: "#10B981",
          accent2: "#22D3EE",
          warn: "#f5b942",
          danger: "#ef4444",
          text: "#E8EEF2",
          subtext: "#87949D",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
