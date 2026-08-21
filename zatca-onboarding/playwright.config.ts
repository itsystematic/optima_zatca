import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end coverage of the onboarding wizard.
 *
 * These drive the real UI against the mock backend — the same code path a user
 * takes. When the Frappe endpoints replace `src/api/mock`, this suite is what
 * proves the swap did not change any behaviour.
 */
export default defineConfig({
	testDir: "./e2e",
	// the live suite has its own config and needs a bench
	testIgnore: /live\.spec\.ts/,
	timeout: 90_000,
	expect: { timeout: 15_000 },
	fullyParallel: false,
	workers: 1,
	reporter: [["list"]],
	use: {
		...devices["Desktop Chrome"],
		baseURL: "http://localhost:8221",
		viewport: { width: 1600, height: 1000 },
	},
	webServer: {
		// the suite drives the in-memory backend, so it needs no bench
		command: "VITE_OZ_API=mock npm run dev -- --port 8221 --strictPort",
		url: "http://localhost:8221/setup",
		reuseExistingServer: !process.env.CI,
		timeout: 60_000,
	},
});
