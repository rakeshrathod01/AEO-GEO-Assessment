/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // eClerx dark navy + red palette.
        navy: {
          950: "#050b1a",
          900: "#0a1430",
          850: "#0d1a3d",
          800: "#122150",
          700: "#1b3066",
          600: "#27407f",
        },
        eclerx: {
          red: "#e4002b",
          "red-dark": "#b80024",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
