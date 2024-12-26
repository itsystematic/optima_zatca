import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";
import proxyOptions from "./proxyOptions";
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // define: {
  //   __: `(text) => text`,
  // },
  server: {
    port: 8200,
    proxy: proxyOptions,
    watch: {
      usePolling: true,
      interval: 100
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    minify: true,
    outDir: "../optima_zatca/public/zatca-onboarding",
    emptyOutDir: true,
    target: "es2015",
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.tsx"),
      output: {
        entryFileNames: "zatca_onboarding.js",
        format: "iife",
        name: 'zatca_onboarding',
      },
    },
  },
});
