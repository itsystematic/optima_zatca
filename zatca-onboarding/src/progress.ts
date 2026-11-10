import type { ZatcaEvent } from "@/types";

/**
 * Turns the "zatca" realtime events into per-register progress.
 *
 * The percentages are the backend's contract (zatca/setup.py, zatca/demo.py):
 *   green 20         compliance CSID issued
 *   green 30…80      a test invoice accepted (+10 each)
 *   red ≥ 20         a test invoice rejected (the percentage does not move)
 *   red 0            a certificate request failed
 *   green 95         production CSID issued
 *   complete         green = live, red = failed (50 when only tests failed)
 */

export const TEST_INVOICES = 6;
const CSID_ISSUED = 20;
const PCSID_ISSUED = 95;

export type Mark = "pending" | "ok" | "failed";
export type RowState = "waiting" | "running" | "live" | "failed";
export type Step = "csid" | "tests" | "pcsid";

export interface RowProgress {
	state: RowState;
	csid: Mark;
	tests: Mark[];
	pcsid: Mark;
	/** ZATCA's own words for the first failure in this attempt. */
	message: string;
	/** "request" when register_company itself was refused, before any step ran. */
	failedAt: Step | "request" | null;
	/** Where this attempt's next test-invoice event lands. */
	cursor: number;
}

export function initialRow(): RowProgress {
	return {
		state: "waiting",
		csid: "pending",
		tests: Array<Mark>(TEST_INVOICES).fill("pending"),
		pcsid: "pending",
		message: "",
		failedAt: null,
		cursor: 0,
	};
}

/**
 * A retry resumes the way add_company_to_zatca does: a CSID already issued is
 * kept, accepted invoices are skipped without an event, rejected ones are sent
 * again in order.
 */
export function startAttempt(row: RowProgress): RowProgress {
	const keep = (m: Mark): Mark => (m === "ok" ? "ok" : "pending");
	return {
		state: "running",
		csid: keep(row.csid),
		tests: row.tests.map(keep),
		pcsid: keep(row.pcsid),
		message: "",
		failedAt: null,
		cursor: 0,
	};
}

export function applyEvent(row: RowProgress, event: ZatcaEvent): RowProgress {
	if (row.state === "live") return row;

	const pct = event.percentage ?? 0;
	const message = event.message ?? "";

	if (event.complete) {
		return event.indicator === "green" ? live(row) : fail(row, message);
	}
	if (event.indicator === "green") {
		if (pct === CSID_ISSUED) return { ...row, state: "running", csid: "ok" };
		if (pct === PCSID_ISSUED) {
			return { ...row, state: "running", csid: "ok", tests: allOk(), pcsid: "ok" };
		}
		if (pct > CSID_ISSUED && pct < PCSID_ISSUED) return markTest(row, "ok", "");
		return { ...row, state: "running" };
	}
	if (event.indicator === "red") {
		if (pct >= CSID_ISSUED) return markTest(row, "failed", message);
		return fail(row, message);
	}
	return { ...row, state: "running" };
}

/** The register_company call itself failed, so no further events will come. */
export function failRequest(row: RowProgress, message: string): RowProgress {
	return row.state === "live" || row.state === "failed" ? row : { ...fail(row, message), failedAt: "request" };
}

/** The step a running row is on, or the one a failed row stopped at. */
export function currentStep(row: RowProgress): Step | null {
	if (row.state === "live") return null;
	if (row.csid !== "ok") return "csid";
	if (row.tests.some((t) => t !== "ok")) return "tests";
	return "pcsid";
}

/** 1-based number of the test invoice this attempt is sending now. */
export function currentTestNumber(row: RowProgress): number {
	const i = nextTest(row);
	return i === -1 ? TEST_INVOICES : i + 1;
}

/**
 * add_company_to_zatca runs the registers of one request one after another,
 * so the first unsettled register is already working before its first event
 * arrives (the CSID request emits nothing until it returns).
 */
export function withImpliedRunning(rows: RowProgress[]): RowProgress[] {
	if (rows.some((r) => r.state === "running")) return rows;
	const i = rows.findIndex((r) => r.state === "waiting");
	if (i === -1) return rows;
	return rows.map((r, j) => (j === i ? { ...r, state: "running" } : r));
}

export function summarize(rows: RowProgress[]) {
	const live = rows.filter((r) => r.state === "live").length;
	const failed = rows.filter((r) => r.state === "failed").length;
	return { total: rows.length, live, failed, settled: live + failed === rows.length };
}

function allOk(): Mark[] {
	return Array<Mark>(TEST_INVOICES).fill("ok");
}

function live(row: RowProgress): RowProgress {
	return { ...row, state: "live", csid: "ok", tests: allOk(), pcsid: "ok", message: "", failedAt: null };
}

function fail(row: RowProgress, message: string): RowProgress {
	const step = currentStep(row);
	return {
		...row,
		state: "failed",
		csid: step === "csid" ? "failed" : row.csid,
		pcsid: step === "pcsid" ? "failed" : row.pcsid,
		message: row.message || message,
		failedAt: step,
	};
}

function nextTest(row: RowProgress): number {
	for (let i = row.cursor; i < row.tests.length; i++) {
		if (row.tests[i] !== "ok") return i;
	}
	return -1;
}

function markTest(row: RowProgress, mark: Mark, message: string): RowProgress {
	const i = nextTest(row);
	if (i === -1) return row;
	const tests = [...row.tests];
	tests[i] = mark;
	return {
		...row,
		state: "running",
		csid: "ok",
		tests,
		cursor: i + 1,
		message: row.message || message,
	};
}
