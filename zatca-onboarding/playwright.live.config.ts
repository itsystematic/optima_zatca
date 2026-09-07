import { defineConfig, devices } from "@playwright/test";

/**
 * The live suite: a real bench, a real session, no mock.
 *
 *   BENCH_SITE=<site> npm run dev -- --port 8322
 *   BENCH_SID=<sid> npm run e2e:live
 *
 * `BENCH_SID` is a session cookie; `BENCH_USER`/`BENCH_PASSWORD` work too.
 * `BENCH_COMPANY` names the company to run against — without it the session's
 * default is used, and the run writes to whatever setup that company has.
 */
export default defineConfig({
	testDir: "./e2e",
	testMatch: /live\.spec\.ts/,
	timeout: 120_000,
	expect: { timeout: 20_000 },
	workers: 1,
	reporter: [["list"]],
	use: {
		...devices["Desktop Chrome"],
		baseURL: process.env.APP_URL ?? "http://localhost:8322",
		viewport: { width: 1600, height: 1000 },
	},
	// unlike the mock suite this needs a dev server pointed at a bench, so it
	// starts one rather than assuming a stray one is still running
	webServer: process.env.APP_URL
		? undefined
		: {
				command: "npm run dev -- --port 8322 --strictPort",
				url: "http://localhost:8322/setup",
				reuseExistingServer: true,
				timeout: 60_000,
			},
});
