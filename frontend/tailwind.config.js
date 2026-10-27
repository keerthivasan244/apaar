/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#1F3A5F", light: "#2C5282", dark: "#152842" },
        teal: { DEFAULT: "#0F6E56", light: "#14906F" },
        page: "#F6F7F9",
        sev: { medium: "#B7791F", high: "#C0392B", critical: "#7B1E1E" },
      },
    },
  },
  plugins: [],
};
