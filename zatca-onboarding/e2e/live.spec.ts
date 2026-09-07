import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * Smoke coverage against a real bench.
 *
 * Read-only by design: it proves the app resumes where the server says it is,
 * renders that state, and never redirects to a step it then refuses. Writing a
 * registration would mutate a real company's setup, which is not something a
 * test suite should decide to do.
 *
 * Skipped unless credentials are supplied.
 */

const SID = process.env.BENCH_SID;
const USER = process.env.BENCH_USER;
const PASSWORD = process.env.BENCH_PASSWORD;
const COMPANY = process.env.BENCH_COMPANY;

test.skip(!SID && !(USER && PASSWORD), "set BENCH_SID, or BENCH_USER and BENCH_PASSWORD, to run");

const app = (p: Page) => p.getByRole("main");

async function signIn(page: Page) {
	if (SID) {
		const { hostname } = new URL(process.env.APP_URL ?? "http://localhost:8322");
		await page.context().addCookies([{ name: "sid", value: SID, domain: hostname, path: "/" }]);
		return;
	}
	const response = await page.request.post("/api/method/login", {
		data: { usr: USER, pwd: PASSWORD },
	});
	expect(response.ok(), "sign-in failed").toBeTruthy();
}

function watch(page: Page): string[] {
	const problems: string[] = [];
	page.on("console", (m) => {
		if (m.type() === "error") problems.push(`console: ${m.text()}`);
	});
	page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
	return problems;
}

test("the wizard resumes on the real setup without looping", async ({ page }) => {
	const problems = watch(page);
	await signIn(page);

	const entry = COMPANY ? `/setup?company=${encodeURIComponent(COMPANY)}` : "/setup";
	await page.goto(entry);
	await expect(app(page).getByRole("heading", { level: 1 })).toContainText("in one sitting");

	// the root resumes wherever the server says this company is — the welcome
	// page when nothing has been started, otherwise the step itself
	await page.goto("/");
	await expect(page).toHaveURL(/\/setup/, { timeout: 20_000 });
	console.log("resumed at", new URL(page.url()).pathname);

	await expect(app(page).getByRole("heading").first()).toBeVisible();

	/**
	 * The loop guard. Every step is visited; a step the server considers current
	 * must never redirect, and any redirect must settle rather than bounce.
	 */
	const steps = ["mode", "scope", "entity", "registers", "review", "otp", "progress", "done"];
	for (const step of steps) {
		await page.goto(`/setup/${step}`);
		await page.waitForTimeout(700);
		const landed = new URL(page.url()).pathname;

		// wherever it landed, staying there must be stable
		await page.goto(landed);
		await page.waitForTimeout(500);
		expect(new URL(page.url()).pathname, `${step} does not settle`).toBe(landed);
	}

	expect(problems, problems.join("\n")).toEqual([]);
});
