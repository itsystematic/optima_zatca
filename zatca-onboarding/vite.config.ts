/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import proxyOptions from "./proxyOptions";

const src = (...parts: string[]) => path.resolve(__dirname, "src", ...parts);

/**
 * The app talks to a real bench by default. `VITE_OZ_API=mock` swaps in the
 * in-memory backend instead, which is what the test suites use and which needs
 * no bench at all.
 *
 * The swap is a resolver alias, not a runtime branch, so exactly one backend
 * enters the module graph. A production build therefore carries no mock data:
 * no fixture companies, no scenario engine, no dev toolbar. `bench build` runs
 * that build, and it never sets the variable.
 */
const mock = process.env.VITE_OZ_API === "mock";

export default defineConfig({
	plugins: [react()],
	// served from Frappe as /assets/optima_zatca/zatca-onboarding/ once built
	base: process.env.NODE_ENV === "production" ? "/assets/optima_zatca/zatca-onboarding/" : "/",
	resolve: {
		// most specific first — Vite takes the first entry that matches
		alias: [
			{
				find: "@/api/backend",
				replacement: mock ? src("api", "mock", "handlers.ts") : src("api", "live.ts"),
			},
			{
				find: "@/dev-toolbar",
				replacement: mock
					? src("components", "DevToolbar.tsx")
					: src("components", "DevToolbar.off.tsx"),
			},
			{ find: "@", replacement: src() },
		],
	},
	server: {
		port: 8200,
		proxy: proxyOptions,
	},
	test: {
		environment: "jsdom",
		include: ["src/**/*.test.ts"],
		// Node 26's own inert `localStorage` shadows the one jsdom installs; the
		// setup file puts a working Storage back. See `src/test/setup.ts`.
		setupFiles: ["./src/test/setup.ts"],
		// the run simulator is driven by real elapsed time, so its tests wait
		testTimeout: 30_000,
	},
	build: {
		outDir: "../optima_zatca/public/zatca-onboarding",
		emptyOutDir: true,
		target: "es2020",
	},
});
