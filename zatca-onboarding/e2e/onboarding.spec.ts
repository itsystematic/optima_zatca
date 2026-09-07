import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * The whole wizard, driven the way an operator drives it.
 *
 * Nothing here reaches into the mock's internals: every assertion is something
 * visible on screen, so the suite keeps its meaning when the backend is real.
 * Locators are scoped to the application region so the development toolbar's
 * own controls never stand in for page content.
 */

const ARABIC_NAME = "مصنع قنديل للزجاج المحدودة";
const TIN = "300123456789003";

const REGISTERS = [
	{
		name: "Riyadh — Head office",
		crn: "1010512345",
		building: "8734",
		street: "King Fahd Road",
		district: "Al Olaya",
		city: "Riyadh",
		postal: "12211",
	},
	{
		name: "Jeddah — Coastal plant",
		crn: "4030298877",
		building: "2219",
		street: "Al Andalus Street",
		district: "Al Rawdah",
		city: "Jeddah",
		postal: "23434",
	},
];

const app = (page: Page) => page.getByRole("main");

/** Every test starts from an empty setup; the mock keeps state in localStorage. */
async function startClean(page: Page) {
	await page.goto("/setup");
	await page.evaluate(() => localStorage.clear());
	await page.goto("/setup");
	await expect(app(page).getByRole("heading", { level: 1 })).toContainText("in one sitting");
}

/**
 * Put the mock into a named state and wait for it to land. The deep link applies
 * the scenario asynchronously, so the hero's call to action is the signal.
 */
async function loadScenario(page: Page, name: string) {
	await page.goto(`/setup?dev=1&scenario=${name}`);
	await expect(
		app(page).getByRole("button", { name: /Resume setup|View your registration/ }),
	).toBeVisible();
}

async function fillRegister(page: Page, r: (typeof REGISTERS)[number]) {
	const form = app(page);
	await form.getByLabel("Commercial register number").fill(r.crn);
	await form.getByLabel("Register name").fill(r.name);
	// the address grid is gated behind a valid identity
	await expect(form.getByText(/unlocked/i)).toBeVisible();
	await form.getByLabel("Building number").fill(r.building);
	await form.getByLabel("Street").fill(r.street);
	await form.getByLabel("District").fill(r.district);
	await form.getByLabel("City").fill(r.city);
	await form.getByLabel("Postal code").fill(r.postal);
}

test.describe("onboarding", () => {
	test("a company goes from nothing to live certificates", async ({ page }) => {
		await startClean(page);
		const ui = app(page);

		// 01 hero → 03 obligation
		await ui.getByRole("button", { name: "Start setup" }).click();
		await expect(ui.getByRole("heading", { name: /Which obligation/ })).toBeVisible();

		// Phase 2 is pre-selected as the recommendation
		await expect(ui.getByText("Selected: Phase 2 — Integration")).toBeVisible();
		await ui.getByRole("button", { name: "Continue" }).click();

		// 04 scope
		await expect(ui.getByRole("heading", { name: /How many commercial registers/ })).toBeVisible();
		await ui.getByRole("radio", { name: /Multiple branches/ }).click();
		await ui.getByLabel("How many do you expect?").fill("2");
		await expect(ui.getByText("2 registers")).toBeVisible();
		await ui.getByRole("button", { name: "Continue" }).click();

		// 05 legal entity — the gate is real
		await expect(ui.getByRole("heading", { name: "Legal entity details" })).toBeVisible();
		const continueBtn = ui.getByRole("button", { name: "Continue" });
		await expect(continueBtn).toBeDisabled();

		await ui.getByLabel("Company").selectOption("Kandil Glass Industries");
		// choosing a company offers its stored defaults
		await expect(ui.getByLabel("Legal name in Arabic")).toHaveValue(ARABIC_NAME);
		await expect(ui.getByLabel("Tax identification number")).toHaveValue("3001234567890");

		// the prefilled TIN is short, and the form says so without being prompted
		await expect(ui.getByText(/2 digits short/)).toBeVisible();
		await expect(ui.getByText("13 / 15")).toBeVisible();
		await expect(continueBtn).toBeDisabled();

		await ui.getByLabel("Tax identification number").fill(TIN);
		await expect(ui.getByText(/2 digits short/)).toBeHidden();
		await expect(continueBtn).toBeEnabled();
		await continueBtn.click();

		// 07 registers, multi-branch variant
		await expect(ui.getByText("Registers added", { exact: true })).toBeVisible();
		await fillRegister(page, REGISTERS[0]);
		await ui.getByRole("button", { name: "Save and add another" }).click();

		await expect(ui.getByText("Riyadh — Head office").first()).toBeVisible();
		await expect(ui.getByText("of 2 expected")).toBeVisible();

		await fillRegister(page, REGISTERS[1]);
		await ui.getByRole("button", { name: "Save register" }).click();

		// 08 review
		await expect(ui.getByRole("heading", { name: /Check every register/ })).toBeVisible();
		await expect(ui.getByText("1010512345")).toBeVisible();
		await expect(ui.getByText("4030298877")).toBeVisible();

		// the irreversible action is gated on the acknowledgement
		const toOtp = ui.getByRole("button", { name: "Continue to OTP entry" });
		await expect(toOtp).toBeDisabled();
		await ui.getByRole("button", { name: /I confirm these details/ }).click();
		await expect(toOtp).toBeEnabled();
		await toOtp.click();

		// 09 OTP modal
		const dialog = page.getByRole("dialog");
		await expect(dialog).toBeVisible();
		await expect(dialog.getByText("0 of 2 entered")).toBeVisible();
		const confirm = dialog.getByRole("button", { name: "Confirm and register" });
		await expect(confirm).toBeDisabled();

		// typing advances between segments on its own
		await dialog.getByLabel("OTP for Riyadh — Head office, digit 1").fill("4");
		await page.keyboard.type("82913");
		await expect(dialog.getByText("1 of 2 entered")).toBeVisible();

		await dialog.getByLabel("OTP for Jeddah — Coastal plant, digit 1").fill("7");
		await page.keyboard.type("05264");
		await expect(dialog.getByText("2 of 2 entered")).toBeVisible();
		await expect(confirm).toBeEnabled();
		await confirm.click();

		// 10 the run
		await expect(ui.getByRole("heading", { name: "Registering 2 commercial registers" })).toBeVisible();
		await expect(ui.getByText("running ·", { exact: false })).toBeVisible();

		// 12 success, reached on its own once every register settles
		await expect(ui.getByRole("heading", { name: /is registered for e-invoicing/ })).toBeVisible({
			timeout: 60_000,
		});
		await expect(page).toHaveURL(/\/setup\/done$/);
		await expect(ui.getByText("2 commercial registers hold live production certificates")).toBeVisible();
		await expect(ui.getByText(/setup reference SETUP-/)).toBeVisible();
	});

	test("a half-finished setup resumes where it was left", async ({ page }) => {
		await startClean(page);
		const ui = app(page);

		await ui.getByRole("button", { name: "Start setup" }).click();
		await ui.getByRole("button", { name: "Continue" }).click(); // obligation
		await ui.getByRole("radio", { name: /Single registration/ }).click();
		await ui.getByRole("button", { name: "Continue" }).click(); // scope

		await expect(ui.getByRole("heading", { name: "Legal entity details" })).toBeVisible();

		// a reload, then landing on the root, must come back to the same step
		await page.goto("/");
		await expect(page).toHaveURL(/\/setup\/entity$/);
		await expect(ui.getByRole("heading", { name: "Legal entity details" })).toBeVisible();

		// and a step that has not been earned bounces back
		await page.goto("/setup/review");
		await expect(page).toHaveURL(/\/setup\/entity$/);
	});

	test("a failed register is explained, isolated, and retried", async ({ page }) => {
		await loadScenario(page, "partial_failure");
		await page.goto("/?dev=1");
		await expect(page).toHaveURL(/\/setup\/progress/);
		const ui = app(page);

		await expect(ui.getByRole("heading", { name: "4 registers are live. 1 needs another attempt." })).toBeVisible();
		await expect(ui.getByText("Failed at compliance certificate")).toBeVisible();
		await expect(ui.getByText("The OTP for this register had already expired.")).toBeVisible();
		await expect(ui.getByText("otp_expired")).toBeVisible();
		await expect(ui.getByText("Live", { exact: true })).toHaveCount(4);

		// this register failed before its certificate was issued, so the authority
		// wants a fresh code and the retry stays closed until one is entered
		const retry = ui.getByRole("button", { name: "Retry this register" });
		await expect(retry).toBeDisabled();
		await expect(ui.getByText(/needs a fresh code/)).toBeVisible();

		await ui.getByLabel("OTP for Dammam — East depot, digit 1").fill("7");
		await page.keyboard.type("41205");
		await expect(retry).toBeEnabled();
		await retry.click();
		await expect(ui.getByRole("heading", { name: /is registered for e-invoicing/ })).toBeVisible({
			timeout: 60_000,
		});
		await expect(ui.getByText("5 commercial registers hold live production certificates")).toBeVisible();
	});

	test("the operator can accept a partial result instead of retrying", async ({ page }) => {
		await loadScenario(page, "partial_failure");
		await page.goto("/?dev=1");
		await expect(page).toHaveURL(/\/setup\/progress/);
		const ui = app(page);

		// a register still wanting a code cannot be swept up by "retry all", so the
		// only action left in the footer is to accept what succeeded
		await expect(ui.getByRole("button", { name: "Retry all failed" })).toBeHidden();
		await ui.getByRole("button", { name: "Continue with 4 registers" }).click();
		await expect(page).toHaveURL(/\/setup\/done$/);
		await expect(ui.getByText(/1 register is still in draft/)).toBeVisible();
		await expect(ui.getByRole("button", { name: "Open the run" })).toBeVisible();
	});

	test("phase 1 never asks for a one-time password", async ({ page }) => {
		await startClean(page);
		const ui = app(page);

		await ui.getByRole("button", { name: "Start setup" }).click();
		await ui.getByRole("radio", { name: /^Phase 1 — Generation/ }).click();
		await expect(ui.getByText("Selected: Phase 1 — Generation")).toBeVisible();
		await ui.getByRole("button", { name: "Continue" }).click();

		await ui.getByRole("radio", { name: /Single registration/ }).click();
		await ui.getByRole("button", { name: "Continue" }).click();

		await ui.getByLabel("Company").selectOption("Kandil Glass Industries");
		await ui.getByLabel("Tax identification number").fill(TIN);
		await ui.getByRole("button", { name: "Continue" }).click();

		await fillRegister(page, REGISTERS[0]);
		await ui.getByRole("button", { name: "Save and continue" }).click();

		// nothing is transmitted and no certificate is issued, so the review page
		// says so and submits from here
		await expect(page).toHaveURL(/\/setup\/review/);
		await expect(ui.getByText(/Phase 1 issues no certificates/)).toBeVisible();
		await expect(ui.getByText("OTPs needed")).toBeHidden();

		await ui.getByRole("button", { name: /I confirm these details/ }).click();
		await ui.getByRole("button", { name: "Register these details" }).click();

		await expect(page).toHaveURL(/\/setup\/done/, { timeout: 30_000 });
		await expect(ui.getByRole("heading", { name: /is registered for e-invoicing/ })).toBeVisible();

		// and the OTP screen is unreachable even by hand
		await page.goto("/setup/otp");
		await expect(page).not.toHaveURL(/\/setup\/otp$/);
	});

	test("the log names which document the authority refused", async ({ page }) => {
		await loadScenario(page, "partial_failure");
		await page.goto("/?dev=1");
		await expect(page).toHaveURL(/\/setup\/progress/);
		const ui = app(page);

		// opening a register's log keeps the run on screen behind it
		await ui.getByRole("button", { name: "View log" }).first().click();
		const drawer = page.getByRole("dialog");
		await expect(drawer).toBeVisible();
		await expect(drawer.getByText("compliance certificate")).toBeVisible();
		await expect(ui.getByRole("heading", { name: /registers are live/ })).toBeVisible();

		await drawer.getByRole("button", { name: "Close" }).click();
		await expect(drawer).toBeHidden();
	});

	test("a refused document is named, in the authority's own words", async ({ page }) => {
		await loadScenario(page, "partial_failure");
		await page.goto("/?dev=1");
		const ui = app(page);

		// the failed register's own panel offers the log directly
		await ui.getByRole("button", { name: "View log" }).nth(2).click();
		const drawer = page.getByRole("dialog");
		await expect(drawer.getByText("Rejected").first()).toBeVisible();
		await expect(drawer.getByText(/no longer valid for this register/)).toBeVisible();
	});

	test("the log page lists every exchange for a chosen register", async ({ page }) => {
		await loadScenario(page, "live");
		await page.goto("/log?dev=1");
		const ui = app(page);

		await expect(
			ui.getByRole("heading", { name: /Every exchange with the authority/ }),
		).toBeVisible();

		// each of the six compliance documents is its own call
		await ui.getByRole("button", { name: /Jeddah/ }).click();
		await expect(ui.getByText("compliance document · simplified invoice")).toBeVisible();
		await expect(ui.getByText("production certificate")).toBeVisible();
		await expect(ui.getByText("Accepted").first()).toBeVisible();
	});

	test("the interface translates and mirrors for Arabic", async ({ page }) => {
		await loadScenario(page, "ready_to_review");
		await page.goto("/?dev=1&lang=ar");
		await expect(page).toHaveURL(/\/setup\/review/);
		const ui = app(page);

		// the whole composition flips, and the copy is Arabic — not English in an
		// Arabic-shaped layout
		await expect(page.locator(".page")).toHaveAttribute("dir", "rtl");
		await expect(page.locator("html")).toHaveAttribute("lang", "ar");
		await expect(ui.getByRole("heading", { name: "راجع كل سجل قبل إصدار الشهادات" })).toBeVisible();

		// Arabic is set in Almarai, not the Latin face falling back to a system font
		const face = await ui
			.getByRole("heading", { name: "راجع كل سجل قبل إصدار الشهادات" })
			.evaluate((el) => getComputedStyle(el).fontFamily);
		expect(face).toContain("Almarai");
		await expect(ui.getByText("المراجعة", { exact: false }).first()).toBeVisible();

		// register numbers stay in Latin digits, as tax documents use
		await expect(ui.getByText("1010512345")).toBeVisible();

		// and the switch takes it back
		await ui.getByRole("button", { name: "English" }).click();
		await expect(page.locator(".page")).toHaveAttribute("dir", "ltr");
		await expect(ui.getByRole("heading", { name: /Check every register/ })).toBeVisible();
	});

	test("Arabic counts agree with the number they describe", async ({ page }) => {
		await loadScenario(page, "partial_failure");
		await page.goto("/?dev=1&lang=ar");
		await expect(page).toHaveURL(/\/setup\/progress/);
		const ui = app(page);

		// four live, one failed: the plural form has to match, not read "4 سجل"
		await expect(ui.getByRole("heading", { name: "4 سجلات نشطة. سجل واحد يحتاج محاولة أخرى." })).toBeVisible();
		await expect(ui.getByText("فشل عند شهادة الامتثال")).toBeVisible();
		await expect(ui.getByRole("button", { name: "المتابعة بـ4 سجلات" })).toBeVisible();
	});
});
