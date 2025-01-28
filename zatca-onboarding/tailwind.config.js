/** @type {import('tailwindcss').Config} */
export default {
  // darkMode: ["class"],
  theme: {
    extend: {
      screens: {
        'laptop': {'raw': '(min-width: 1366px) and (max-width: 1600px)'},
      }
    }
  },
  daisyui: {
    themes: ['light'],
  },
  content: ["./src/**/*.{html,jsx,tsx,vue,js,ts}"],
  important: true,
  plugins: [],
};
