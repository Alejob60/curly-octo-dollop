/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#09111f",
        mist: "#f5efe3",
        copper: "#a65a3a",
        moss: "#386641",
        signal: "#f4d35e",
        steel: "#51606f",
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        body: ["Segoe UI", "sans-serif"],
      },
      boxShadow: {
        panel: "0 24px 80px rgba(9, 17, 31, 0.18)",
      },
      animation: {
        floatIn: "floatIn 0.6s ease-out both",
        pulseLine: "pulseLine 1.8s ease-in-out infinite",
      },
      keyframes: {
        floatIn: {
          "0%": { opacity: 0, transform: "translateY(24px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        pulseLine: {
          "0%, 100%": { opacity: 0.35 },
          "50%": { opacity: 1 },
        },
      },
    },
  },
  plugins: [],
};