/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f5f7ff",
          100: "#e6ecff",
          200: "#c8d6ff",
          300: "#9ab3ff",
          400: "#6a87ff",
          500: "#3d5cff",
          600: "#2a40e6",
          700: "#1f30b3",
          800: "#162180",
          900: "#0d154d",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "Segoe UI", "Roboto"],
      },
    },
  },
  plugins: [],
};
