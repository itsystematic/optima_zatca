import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { qk } from "./keys";
import { resetForCompanySwitch } from "./setup";

/** A cache in the state it would be in on the summary screen of a finished setup. */
function warm() {
	const qc = new QueryClient();
	qc.setQueryData(qk.setup, { id: "S", company: "A", status: "live" });
	qc.setQueryData(qk.phaseOptions, [{ phase: "phase_2" }]);
	qc.setQueryData(qk.registerLog("R1"), [{ id: "L1" }]);
	qc.setQueryData(qk.companies, [
		{ name: "A", status: "draft" },
		{ name: "B", status: "not_started" },
	]);
	qc.setQueryData(qk.cities, [{ name: "Riyadh" }]);
	qc.setQueryData(qk.guidance, { phases: [] });
	return qc;
}

describe("switching company", () => {
	it("forgets the previous company's setup outright", () => {
		const qc = warm();
		resetForCompanySwitch(qc);
		expect(qc.getQueryData(qk.setup)).toBeUndefined();
		expect(qc.getQueryData(qk.phaseOptions)).toBeUndefined();
		expect(qc.getQueryData(qk.registerLog("R1"))).toBeUndefined();
	});

	/**
	 * The reported bug: the list carries each company's setup status and is held
	 * indefinitely, so the company just registered still read as unregistered on
	 * the picker until the page was reloaded.
	 */
	it("marks the company list stale, so the picker refetches the new status", () => {
		const qc = warm();
		resetForCompanySwitch(qc);

		const state = qc.getQueryState(qk.companies);
		expect(state?.isInvalidated, "company list was not invalidated").toBe(true);
	});

	it("keeps the list itself, so the picker has something to draw immediately", () => {
		const qc = warm();
		resetForCompanySwitch(qc);
		expect(qc.getQueryData(qk.companies)).toHaveLength(2);
	});

	it("leaves reference data alone — it does not depend on the company", () => {
		const qc = warm();
		resetForCompanySwitch(qc);
		expect(qc.getQueryState(qk.cities)?.isInvalidated).toBe(false);
		expect(qc.getQueryState(qk.guidance)?.isInvalidated).toBe(false);
		expect(qc.getQueryData(qk.cities)).toBeDefined();
	});
});
