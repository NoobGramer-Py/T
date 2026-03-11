/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gold:   { DEFAULT: "#ffb300", bright: "#ffe566", deep: "#ff6e00" },
        threat: { low: "#00ff88", mid: "#ffb300", high: "#ff4400" },
        hud:    { bg: "#000409", panel: "rgba(255,179,0,0.04)", border: "rgba(255,179,0,0.15)" },
      },
      fontFamily: {
        mono: ["'Courier New'", "Courier", "monospace"],
      },
      animation: {
        "pulse-gold": "pulse-gold 2s ease-in-out infinite",
        "scanline":   "scanline 4s linear infinite",
      },
      keyframes: {
        "pulse-gold": {
          "0%, 100%": { opacity: "0.4" },
          "50%":       { opacity: "1"   },
        },
        "scanline": {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
      },
    },
  },
  plugins: [],
};
