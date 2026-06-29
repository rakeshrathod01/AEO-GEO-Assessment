/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // eClerx-leaning palette; tune in later phases.
        brand: {
          DEFAULT: "#0b5fff",
          dark: "#0a2540",
        },
      },
    },
  },
  plugins: [],
};
