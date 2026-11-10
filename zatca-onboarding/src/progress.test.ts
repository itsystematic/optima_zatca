import { describe, expect, it } from "vitest";
import {
	applyEvent,
	currentStep,
	currentTestNumber,
	failRequest,
	initialRow,
	startAttempt,
	summarize,
	withImpliedRunning,
	type RowProgress,
} from "@/progress";
import type { ZatcaEvent } from "@/types";

const CRN = "1010000001";
const green = (percentage: number, extra: Partial<ZatcaEvent> = {}): ZatcaEvent => ({
	indicator: "green",
	percentage,
	commercial_register_name: CRN,
	...extra,
});
const red = (percentage: number, extra: Partial<ZatcaEvent> = {}): ZatcaEvent => ({
	indicator: "red",
	percentage,
	commercial_register_name: CRN,
	...extra,
});
const run = (row: RowProgress, events: ZatcaEvent[]) => events.reduce(applyEvent, row);

const ACCEPT_ALL = [30, 40, 50, 60, 70, 80].map((p) => green(p));
const DONE = green(100, { complete: true, message: "ZATCA Setup Completed" });

describe("applyEvent", () => {
	it("reaches live through the whole v15 sequence", () => {
		const row = run(initialRow(), [green(20), ...ACCEPT_ALL, green(95), DONE]);
		expect(row.state).toBe("live");
		expect(row.tests.every((t) => t === "ok")).toBe(true);
		expect(row.pcsid).toBe("ok");
	});

	it("keeps going after a rejected invoice and fails at the end on the rejection message", () => {
		const rejected = "Invoice Standard  Type credit Was Rejected in Zatca";
		const row = run(initialRow(), [
			green(20),
			green(30),
			green(40),
			green(50),
			red(50, { message: rejected }),
			green(60),
			green(70),
			red(50, { complete: true, message: "ZATCA Setup Partially Completed" }),
		]);
		expect(row.state).toBe("failed");
		expect(row.tests).toEqual(["ok", "ok", "ok", "failed", "ok", "ok"]);
		expect(row.message).toBe(rejected);
		expect(row.failedAt).toBe("tests");
		expect(row.pcsid).toBe("pending");
	});

	it("marks the CSID failed and keeps the first, more specific message", () => {
		const row = run(initialRow(), [
			red(0, { message: "Failed during CSID creation: Invalid OTP" }),
			red(0, { complete: true, message: "ZATCA Setup Failed: Invalid OTP" }),
		]);
		expect(row.state).toBe("failed");
		expect(row.csid).toBe("failed");
		expect(row.message).toBe("Failed during CSID creation: Invalid OTP");
	});

	it("blames the production CSID when every test invoice passed", () => {
		const row = run(initialRow(), [green(20), ...ACCEPT_ALL, red(0, { message: "boom" })]);
		expect(row.pcsid).toBe("failed");
		expect(row.csid).toBe("ok");
		expect(currentStep(row)).toBe("pcsid");
	});

	it("ignores events once a row is live", () => {
		const live = run(initialRow(), [green(20), ...ACCEPT_ALL, green(95), DONE]);
		expect(applyEvent(live, red(0, { complete: true }))).toBe(live);
	});
});

describe("startAttempt", () => {
	it("re-sends only the rejected invoice, as demo.py skips accepted ones silently", () => {
		const failed = run(initialRow(), [
			green(20),
			green(30),
			green(40),
			green(50),
			red(50, { message: "rejected" }),
			green(60),
			green(70),
			red(50, { complete: true }),
		]);
		const retry = startAttempt(failed);
		expect(retry.state).toBe("running");
		expect(retry.message).toBe("");
		expect(currentTestNumber(retry)).toBe(4);

		// The backend restarts its percentage at 20, so the re-sent invoice reports 30.
		const row = run(retry, [green(30), green(95), DONE]);
		expect(row.tests.every((t) => t === "ok")).toBe(true);
		expect(row.state).toBe("live");
	});

	it("asks for the CSID again after a CSID failure", () => {
		const failed = run(initialRow(), [red(0, { complete: true, message: "Invalid OTP" })]);
		const retry = startAttempt(failed);
		expect(retry.csid).toBe("pending");
		expect(run(retry, [green(20), ...ACCEPT_ALL, green(95), DONE]).state).toBe("live");
	});
});

describe("board helpers", () => {
	it("treats the first waiting register as running until one reports", () => {
		const rows = withImpliedRunning([initialRow(), initialRow()]);
		expect(rows.map((r) => r.state)).toEqual(["running", "waiting"]);

		const reporting = [initialRow(), applyEvent(initialRow(), green(20))];
		expect(withImpliedRunning(reporting).map((r) => r.state)).toEqual(["waiting", "running"]);
	});

	it("fails only unsettled rows when the request itself fails", () => {
		const live = run(initialRow(), [DONE]);
		const rows = [live, initialRow()].map((r) => failRequest(r, "Company Foo Not Found"));
		expect(rows.map((r) => r.state)).toEqual(["live", "failed"]);
		expect(rows[1].message).toBe("Company Foo Not Found");
		expect(rows[1].failedAt).toBe("request");
		expect(summarize(rows)).toEqual({ total: 2, live: 1, failed: 1, settled: true });
	});
});
