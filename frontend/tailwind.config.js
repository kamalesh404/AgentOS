/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        night: "#0a0613",
        panel: "#130b24",
      },
    },
  },
  plugins: [],
};
