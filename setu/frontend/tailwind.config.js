export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        periwinkle: "#7285C2",
        violet: "#95709F",
        petal: "#EBD2DA",
        cream: "#F7F2E9",
        plum: "#2E2136",
        signal: "#BC1F2B",
        teal: "#2F9599",
        amber: "#C08010",
      },
      fontFamily: {
        display: ["'Lobster Two'", "cursive"],
        sans: ["'Space Grotesk'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "1.5rem",
      },
      boxShadow: {
        soft: "0 10px 30px -12px rgba(46, 33, 54, 0.18)",
      },
    },
  },
  plugins: [],
};
