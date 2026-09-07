import { describe, expect, it } from "vitest";
import type { Setup } from "@/api";
import { STEP_ORDER, canReach, effectiveStep, needsOtp, stepPath } from "./paths";

/** A setup record with only the fields the guard reads. */
const setup = (over: Partial<Setup>): Setup =>
	({
		id: "S",
		company: "C",
		status: "draft",
		step: "mode",
		phase: null,
		scope: null,
		entity: null,
		entityVerifiedOn: null,
		expectedRegisters: null,
		registers: [],
		acknowledged: false,
		reference: null,
		startedAt: null,
		completedAt: null,
		modified: "",
		...over,
	}) as Setup;

describe("phase 1 skips the one-time password", () => {
	const phaseOne = setup({
		step: "otp",
		phase: "phase_1",
		scope: "single",
		entity: { company: "C", legalNameAr: "ا", tin: "3" },
		acknowledged: true,
		registers: [{ id: "R1" }] as Setup["registers"],
	});

	it("never opens the OTP screen", () => {
		expect(canReach("otp", phaseOne)).toBe(false);
		expect(needsOtp(phaseOne)).toBe(false);
	});

	it("resumes on review, where the submission is made instead", () => {
		expect(effectiveStep(phaseOne)).toBe("review");
		expect(canReach("review", phaseOne)).toBe(true);
	});

	it("leaves phase 2 alone", () => {
		const phaseTwo = { ...phaseOne, phase: "phase_2" } as Setup;
		expect(needsOtp(phaseTwo)).toBe(true);
		expect(canReach("otp", phaseTwo)).toBe(true);
		expect(effectiveStep(phaseTwo)).toBe("otp");
	});
});

describe("step guard", () => {
	it("opens nothing beyond the first step on an empty setup", () => {
		const s = setup({});
		expect(canReach("mode", s)).toBe(true);
		expect(canReach("scope", s)).toBe(false);
		expect(canReach("review", s)).toBe(false);
	});

	it("opens review as soon as one register exists, mid-list", () => {
		const s = setup({
			step: "registers",
			phase: "phase_2",
			scope: "multiple",
			entity: { company: "C", legalNameAr: "ا", tin: "3" },
			expectedRegisters: 5,
			registers: [{ id: "R1" }] as Setup["registers"],
		});
		expect(canReach("registers", s)).toBe(true);
		expect(canReach("review", s)).toBe(true);
		expect(canReach("otp", s)).toBe(false);
	});

	/**
	 * The one that matters: the server can report a step this file's own rules
	 * would refuse — a run started by a retry never sets `startedAt`. Redirecting
	 * away from it would land on the same route and loop forever.
	 */
	it("never refuses the step the server says the operator is on", () => {
		for (const step of STEP_ORDER) {
			// phase 1 is the one deliberate exception, covered above
			const s = setup({ step, phase: "phase_2" });
			expect(canReach(step, s), `${step} refused while current`).toBe(true);
		}
	});

	it("cannot redirect a step to itself", () => {
		const running = setup({ step: "progress", status: "running", startedAt: null });
		expect(canReach("progress", running)).toBe(true);
		expect(stepPath[running.step]).toBe("/setup/progress");
	});

	it("still refuses a step the operator has not earned", () => {
		const s = setup({ step: "scope", phase: "phase_2" });
		expect(canReach("entity", s)).toBe(false);
		expect(canReach("done", s)).toBe(false);
	});
});

describe("a settled registration is not a form", () => {
	it("opens nothing but the summary once certificates are issued", () => {
		const done = setup({
			status: "live",
			step: "done",
			completedAt: "2026-08-19T09:00:00",
		});
		for (const step of STEP_ORDER) {
			expect(canReach(step, done), step).toBe(step === "done");
		}
	});

	it("refuses a pasted URL for an earlier decision", () => {
		const done = setup({
			status: "live",
			step: "done",
			completedAt: "2026-08-19T09:00:00",
		});
		// the decision behind a live certificate is binding, and the server would
		// refuse the write regardless — so the screen has nothing to offer
		expect(canReach("mode", done)).toBe(false);
		expect(canReach("registers", done)).toBe(false);
	});

	it("holds a run in flight on the progress board", () => {
		const running = setup({
			status: "running",
			step: "progress",
			startedAt: "2026-08-19T09:00:00",
		});
		for (const step of STEP_ORDER) {
			expect(canReach(step, running), step).toBe(step === "progress");
		}
	});

	it("still opens the run after a partial one was accepted, so it can be retried", () => {
		// `finish_with_live` sets both `completedAt` and `partial`: the operator
		// accepted the run as it stood, with registers still outstanding. The done
		// screen offers to finish them, and the retry that does it is on the
		// progress board — so that one step has to stay reachable. Guarding it the
		// same way as a fully live setup made the button navigate straight back to
		// the screen it was pressed on.
		const accepted = setup({
			status: "partial",
			step: "done",
			startedAt: "2026-08-19T09:00:00",
			completedAt: "2026-08-19T09:20:00",
		});
		expect(canReach("progress", accepted)).toBe(true);
		expect(canReach("done", accepted)).toBe(true);
		// everything else is still settled
		expect(canReach("registers", accepted)).toBe(false);
		expect(canReach("otp", accepted)).toBe(false);
	});

	it("opens nothing but the summary once every register is live", () => {
		const live = setup({
			status: "live",
			step: "done",
			completedAt: "2026-08-19T09:00:00",
		});
		expect(canReach("progress", live)).toBe(false);
	});

	it("holds a partly failed run there too, where the retry lives", () => {
		const partial = setup({
			status: "partial",
			step: "progress",
			startedAt: "2026-08-19T09:00:00",
		});
		expect(canReach("progress", partial)).toBe(true);
		expect(canReach("registers", partial)).toBe(false);
	});
})
