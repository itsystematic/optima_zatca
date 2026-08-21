import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../types";
import { db } from "./db";
import * as api from "./handlers";
import { DEMO_REGISTERS } from "./seed";

/**
 * The wizard's state machine, exercised through the same functions the UI calls.
 * When these become real Frappe endpoints this file is the contract they have to
 * keep satisfying.
 */

const ENTITY = {
	company: "Kandil Glass Industries",
	legalNameAr: "مصنع قنديل للزجاج المحدودة",
	tin: "300123456789003",
};

const registerInput = (i: number) => ({
	registerName: DEMO_REGISTERS[i].registerName,
	crn: DEMO_REGISTERS[i].crn,
	address: DEMO_REGISTERS[i].address,
});

/** Walk the wizard to the point where only the OTPs are outstanding. */
async function fillTo(registerCount: number) {
	await api.saveMode({ phase: "phase_2" });
	await api.saveScope({ scope: "multiple", expectedRegisters: registerCount });
	await api.saveEntity(ENTITY);
	for (let i = 0; i < registerCount; i++) await api.addRegister(registerInput(i));
	return api.setAcknowledged(true);
}

const otpFor = (ids: string[]) => ({ entries: ids.map((id) => ({ registerId: id, code: "482913" })) });

beforeEach(async () => {
	localStorage.clear();
	db.reset();
	vi.useRealTimers();
	// compress the simulator so a full five-stage run finishes in a second or two
	await api.setSpeed(0.08);
});

describe("step progression", () => {
	it("starts with nothing and asks for the obligation first", async () => {
		const setup = await api.getSetup();
		expect(setup.status).toBe("not_started");
		expect(setup.step).toBe("mode");
	});

	it("advances one step per decision", async () => {
		expect((await api.saveMode({ phase: "phase_2" })).step).toBe("scope");
		expect((await api.saveScope({ scope: "single" })).step).toBe("entity");
		expect((await api.saveEntity(ENTITY)).step).toBe("registers");
		expect((await api.addRegister(registerInput(0))).step).toBe("review");
		expect((await api.setAcknowledged(true)).step).toBe("otp");
	});

	it("survives a reload, because progress is persisted not remembered", async () => {
		await api.saveMode({ phase: "phase_1" });
		await api.saveScope({ scope: "single" });
		// a fresh module-level read is what a reload does
		expect((await api.getSetup()).phase).toBe("phase_1");
		expect((await api.getSetup()).step).toBe("entity");
	});
});

describe("validation at the boundary", () => {
	it("refuses a short TIN and names the field", async () => {
		await api.saveMode({ phase: "phase_2" });
		await api.saveScope({ scope: "single" });
		const failure = await api.saveEntity({ ...ENTITY, tin: "3001" }).catch((e) => e);
		expect(failure).toBeInstanceOf(ApiError);
		expect(failure.fieldErrors.map((f: { field: string }) => f.field)).toContain("tin");
	});

	it("refuses a duplicate commercial register number", async () => {
		await fillTo(2);
		const failure = await api.addRegister(registerInput(0)).catch((e) => e);
		expect(failure).toBeInstanceOf(ApiError);
		expect(failure.fieldErrors[0].key).toBe("validation.crn.duplicate");
	});

	it("drops the acknowledgement when the register list changes underneath it", async () => {
		const acknowledged = await fillTo(2);
		expect(acknowledged.acknowledged).toBe(true);
		const after = await api.addRegister(registerInput(2));
		expect(after.acknowledged).toBe(false);
		expect(after.step).toBe("review");
	});

	it("will not start a run with a code missing", async () => {
		const setup = await fillTo(3);
		const partial = { entries: [{ registerId: setup.registers[0].id, code: "482913" }] };
		await expect(api.submitOtp(partial)).rejects.toBeInstanceOf(ApiError);
		expect((await api.getSetup()).status).toBe("draft");
	});
});

describe("the run", () => {
	it("moves every register through five stages to a live certificate", async () => {
		const setup = await fillTo(2);
		const started = await api.submitOtp(otpFor(setup.registers.map((r) => r.id)));
		expect(started.status).toBe("running");
		expect(started.reference).toMatch(/^SETUP-/);

		await vi.waitFor(
			async () => {
				const now = await api.getSetup();
				expect(now.status).toBe("live");
			},
			{ timeout: 15_000, interval: 50 },
		);

		const finished = await api.getSetup();
		expect(finished.completedAt).not.toBeNull();
		expect(finished.registers.every((r) => r.status === "live")).toBe(true);
		expect(finished.registers[0].certificate?.fingerprint).toMatch(/^[0-9a-f]{2}(:[0-9a-f]{2}){7}$/);
		expect(Object.values(finished.registers[0].run!.stages)).toEqual(
			Array(5).fill("done"),
		);
	});

	it("locks editing while the run is in flight", async () => {
		const setup = await fillTo(2);
		await api.submitOtp(otpFor(setup.registers.map((r) => r.id)));
		await expect(api.addRegister(registerInput(3))).rejects.toBeInstanceOf(ApiError);
	});

	it("fails one register without touching the others, and retries it clean", async () => {
		await api.setFailureMode("one_otp_expired");
		const setup = await fillTo(4);
		await api.submitOtp(otpFor(setup.registers.map((r) => r.id)));

		await vi.waitFor(
			async () => {
				expect((await api.getSetup()).status).toBe("partial");
			},
			{ timeout: 15_000, interval: 50 },
		);

		const failedRun = await api.getSetup();
		const failed = failedRun.registers.filter((r) => r.status === "failed");
		expect(failed).toHaveLength(1);
		expect(failed[0].run?.error?.code).toBe("otp_expired");
		expect(failed[0].run?.error?.attempt).toBe(1);
		expect(failed[0].run?.stage).toBe("compliance");
		expect(failedRun.registers.filter((r) => r.status === "live")).toHaveLength(3);
		// the failure is not fatal: the run is finished, not stuck
		expect(failedRun.completedAt).toBeNull();

		await api.retryRegisters([failed[0].id]);
		await vi.waitFor(
			async () => {
				expect((await api.getSetup()).status).toBe("live");
			},
			{ timeout: 15_000, interval: 50 },
		);

		const retried = await api.getSetup();
		expect(retried.registers.every((r) => r.status === "live")).toBe(true);
		// the successful registers were never re-run
		expect(retried.registers[0].certificate).not.toBeNull();
	});

	it("lets the operator accept a partial result and finish", async () => {
		await api.setFailureMode("one_otp_expired");
		const setup = await fillTo(3);
		await api.submitOtp(otpFor(setup.registers.map((r) => r.id)));
		await vi.waitFor(
			async () => {
				expect((await api.getSetup()).status).toBe("partial");
			},
			{ timeout: 15_000, interval: 50 },
		);

		const done = await api.finishWithLive();
		expect(done.completedAt).not.toBeNull();
		expect(done.step).toBe("done");
	});
});

describe("phase 1", () => {
	/**
	 * Phase 1 transmits nothing and issues no certificate, so a one-time password
	 * would authorise an exchange that never happens. Asking for one is not a
	 * cosmetic wrong step — it sends the operator to the portal for a code that
	 * cannot be used.
	 */
	async function phaseOneTo(registerCount: number) {
		await api.saveMode({ phase: "phase_1" });
		await api.saveScope({ scope: "multiple", expectedRegisters: registerCount });
		await api.saveEntity(ENTITY);
		for (let i = 0; i < registerCount; i++) await api.addRegister(registerInput(i));
		return api.setAcknowledged(true);
	}

	it("accepts a submission with no codes at all", async () => {
		await phaseOneTo(2);
		const done = await api.submitOtp({ entries: [] });
		expect(done.status).toBe("live");
		expect(done.step).toBe("done");
		expect(done.completedAt).not.toBeNull();
		expect(done.registers.every((r) => r.status === "live")).toBe(true);
		expect(done.reference).toMatch(/^SETUP-/);
	});

	it("still refuses to start without the acknowledgement", async () => {
		await api.saveMode({ phase: "phase_1" });
		await api.saveScope({ scope: "single" });
		await api.saveEntity(ENTITY);
		await api.addRegister(registerInput(0));
		await expect(api.submitOtp({ entries: [] })).rejects.toBeInstanceOf(ApiError);
	});

	it("leaves phase 2 demanding a code for every register", async () => {
		await fillTo(2);
		await expect(api.submitOtp({ entries: [] })).rejects.toBeInstanceOf(ApiError);
	});
});

describe("scenarios", () => {
	it.each([
		["multi_draft", "registers"],
		["ready_to_review", "review"],
		["awaiting_otp", "otp"],
		["running", "progress"],
	] as const)("%s lands on the %s step", async (scenario, step) => {
		const setup = await api.applyScenario(scenario);
		expect(setup.step).toBe(step);
	});

	it("partial_failure arrives already settled with one failure", async () => {
		const setup = await api.applyScenario("partial_failure");
		expect(setup.status).toBe("partial");
		expect(setup.registers.filter((r) => r.status === "failed")).toHaveLength(1);
		expect(setup.registers.filter((r) => r.status === "live")).toHaveLength(4);
	});

	it("live arrives complete", async () => {
		const setup = await api.applyScenario("live");
		expect(setup.status).toBe("live");
		expect(setup.completedAt).not.toBeNull();
		expect(setup.step).toBe("done");
	});
});
