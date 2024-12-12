/** @type {import('tailwindcss').Config} */
export default {
  // darkMode: ["class"],
  daisyui: {
    themes: ['light'],
  },
  content: ["./src/**/*.{html,jsx,tsx,vue,js,ts}"],
  important: true,
  plugins: [require("daisyui")],
};
