import { ApiError } from "../types";
import type {
	City,
	Company,
	Guidance,
	PhaseOption,
	LogEntry,
	LogOutcome,
	Register,
	RegisterInput,
	SaveEntityInput,
	SaveModeInput,
	SaveScopeInput,
	OtpEntry,
	Setup,
	SetupStep,
	SubmitOtpInput,
} from "../types";
import { validateEntity, validateRegister, otpProblem } from "@/lib/validation";
import { db } from "./db";
import type { MockState } from "./db";
import { STAGGER_MS, runDurationMs, runFor } from "./engine";
import { CITIES, COMPANIES, DEMO_REGISTERS, EMPTY_ADDRESS, GUIDANCE, emptySetup } from "./seed";

/**
 * The mock backend.
 *
 * Every function here stands in for one whitelisted Frappe method. They validate
 * their input, mutate the store, and return the whole `Setup` — the same
 * read-after-write shape the real endpoints will use, so the query cache can be
 * primed from a mutation response instead of refetching.
 */

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Reads feel instant; writes feel like a round trip. */
const readDelay = () => sleep(90 + Math.random() * 120);
const writeDelay = () => sleep(260 + Math.random() * 260);

/* ── Derived state ──────────────────────────────────────────────────────── */

/**
 * Where the operator should pick up.
 *
 * This is deliberately not the same question as "what am I allowed to open" —
 * having said to expect five registers and entered three, the natural place to
 * resume is the register form, even though the review page is perfectly
 * reachable. `canReach` in `routes/paths` answers the permission question.
 */
export function resumeStep(s: Setup): SetupStep {
	if (s.completedAt) return "done";
	if (s.status === "running" || s.status === "partial") return "progress";
	if (!s.phase) return "mode";
	if (!s.scope) return "scope";
	if (!s.entity) return "entity";
	if (s.registers.length === 0) return "registers";
	if (s.expectedRegisters && s.registers.length < s.expectedRegisters) return "registers";
	if (!s.acknowledged) return "review";
	return "otp";
}

/**
 * Advance any in-flight run to the present moment.
 *
 * The real backend has a worker doing this and writing rows; here the read path
 * derives it from elapsed time, which keeps the result identical across reloads.
 */
function tick(state: MockState): Setup {
	const s = state.setup;
	if (!s.startedAt || s.completedAt) {
		s.step = resumeStep(s);
		return s;
	}

	const now = Date.now();
	let settled = true;
	let anyFailed = false;

	s.registers = s.registers.map((register) => {
		const startedAt = state.runStartedAt[register.id];
		if (!startedAt) return register; // added after this run began; still a draft

		const outcome = runFor({
			register,
			elapsedMs: now - Date.parse(startedAt),
			speed: state.speed,
			failAt: state.failing[register.id] ?? null,
			attempt: state.attempts[register.id] ?? 1,
			startedAt,
		});

		if (outcome.status === "queued" || outcome.status === "running") settled = false;
		if (outcome.status === "failed") anyFailed = true;

		return {
			...register,
			status: outcome.status,
			run: outcome.run,
			certificate: outcome.certificate ?? register.certificate,
		};
	});

	if (settled) {
		s.status = anyFailed ? "partial" : "live";
		if (!anyFailed) {
			s.completedAt = new Date().toISOString();
		}
	} else {
		s.status = "running";
	}

	s.step = resumeStep(s);
	return s;
}

function current(): Setup {
	return db.write((d) => {
		tick(d);
	}).setup;
}

function clone<T>(value: T): T {
	return JSON.parse(JSON.stringify(value)) as T;
}

function nextRegisterId(s: Setup): string {
	const used = s.registers.map((r) => Number(r.id.replace(/\D/g, "")) || 0);
	return `REG-${String(Math.max(0, ...used) + 1).padStart(4, "0")}`;
}

function reindex(registers: Register[]): Register[] {
	return registers.map((r, i) => ({ ...r, index: i + 1 }));
}

function requireDraft(s: Setup) {
	if (s.status === "running") {
		throw new ApiError("api.alreadyRunning", { status: 409 });
	}
	if (s.completedAt) {
		throw new ApiError("api.alreadyComplete", { status: 409 });
	}
}

/* ── Reads ──────────────────────────────────────────────────────────────── */

export async function getSetup(): Promise<Setup> {
	await readDelay();
	return clone(current());
}

export async function getGuidance(): Promise<Guidance> {
	await readDelay();
	return clone(GUIDANCE);
}

export async function getCompanies(): Promise<Company[]> {
	await readDelay();
	return clone(COMPANIES);
}

/**
 * The mock company is fully configured, so nothing blocks it. The shape still
 * carries the note phase two always carries, because the interface has to render
 * that path and a mock that never produces one would hide it.
 */
export async function getPhaseOptions(): Promise<PhaseOption[]> {
	await readDelay();
	return [
		{ phase: "phase_1", eligible: true, blockers: [], notes: [], recommended: false },
		{
			phase: "phase_2",
			eligible: true,
			blockers: [],
			notes: [{ key: "eligibility.note.waveIsAuthorityAssigned" }],
			recommended: true,
			recommendedBecause: "eligibility.because.registeredAndConfigured",
		},
	];
}

export async function getCities(): Promise<City[]> {
	await readDelay();
	return clone(CITIES);
}

/* ── Decisions ──────────────────────────────────────────────────────────── */

export async function saveMode(input: SaveModeInput): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			d.setup.phase = input.phase;
			d.setup.status = "draft";
			tick(d);
		}).setup,
	);
}

export async function saveScope(input: SaveScopeInput): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			d.setup.scope = input.scope;
			d.setup.expectedRegisters =
				input.scope === "single" ? 1 : (input.expectedRegisters ?? d.setup.expectedRegisters ?? null);
			tick(d);
		}).setup,
	);
}

export async function saveEntity(input: SaveEntityInput): Promise<Setup> {
	await writeDelay();
	const errors = validateEntity(input);
	if (errors.length) throw new ApiError("api.fixHighlighted", { fieldErrors: errors });

	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			d.setup.company = input.company;
			d.setup.entity = { ...input };
			tick(d);
		}).setup,
	);
}

export async function markEntityVerified(): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			d.setup.entityVerifiedOn = new Date().toISOString();
		}).setup,
	);
}

/* ── Registers ──────────────────────────────────────────────────────────── */

function buildRegister(id: string, index: number, input: RegisterInput): Register {
	return {
		id,
		index,
		environment: "sandbox",
		registerName: input.registerName.trim(),
		crn: input.crn,
		address: { ...EMPTY_ADDRESS, ...input.address, country: EMPTY_ADDRESS.country },
		status: "draft",
		run: null,
		certificate: null,
	};
}

export async function addRegister(input: RegisterInput): Promise<Setup> {
	await writeDelay();
	const taken = db.read().setup.registers.map((r) => r.crn);
	const errors = validateRegister(input, { takenCrns: taken });
	if (errors.length) throw new ApiError("api.fixHighlighted", { fieldErrors: errors });

	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			const id = nextRegisterId(d.setup);
			d.setup.registers = reindex([
				...d.setup.registers,
				buildRegister(id, d.setup.registers.length + 1, input),
			]);
			// adding a register invalidates the acknowledgement on the review page
			d.setup.acknowledged = false;
			tick(d);
		}).setup,
	);
}

export async function updateRegister(id: string, input: RegisterInput): Promise<Setup> {
	await writeDelay();
	const existing = db.read().setup.registers;
	const taken = existing.filter((r) => r.id !== id).map((r) => r.crn);
	const errors = validateRegister(input, { takenCrns: taken });
	if (errors.length) throw new ApiError("api.fixHighlighted", { fieldErrors: errors });

	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			const target = d.setup.registers.find((r) => r.id === id);
			if (!target) throw new ApiError("api.registerGone", { status: 404 });
			if (target.status === "live") {
				throw new ApiError("api.liveNoEdit", { status: 409 });
			}
			target.registerName = input.registerName.trim();
			target.crn = input.crn;
			target.address = { ...target.address, ...input.address, country: EMPTY_ADDRESS.country };
			d.setup.acknowledged = false;
			tick(d);
		}).setup,
	);
}

export async function removeRegister(id: string): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			const target = d.setup.registers.find((r) => r.id === id);
			if (target?.status === "live") {
				throw new ApiError("api.liveNoRemove", { status: 409 });
			}
			d.setup.registers = reindex(d.setup.registers.filter((r) => r.id !== id));
			d.setup.acknowledged = false;
			tick(d);
		}).setup,
	);
}

export async function setAcknowledged(value: boolean): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			requireDraft(d.setup);
			d.setup.acknowledged = value;
			tick(d);
		}).setup,
	);
}

/* ── The run ────────────────────────────────────────────────────────────── */

function beginRun(d: MockState, registerIds: string[]) {
	const now = Date.now();
	const s = d.setup;

	s.reference ??= `SETUP-${(Math.abs(hashOf(s.id + now)) % 0xffff).toString(16).toUpperCase().padStart(4, "0")}`;
	s.startedAt = new Date(now).toISOString();
	s.completedAt = null;
	s.status = "running";

	registerIds.forEach((id, i) => {
		d.runStartedAt[id] = new Date(now + i * STAGGER_MS * d.speed).toISOString();
		d.attempts[id] = (d.attempts[id] ?? 0) + 1;
		const target = s.registers.find((r) => r.id === id);
		if (target) {
			target.status = "queued";
			target.run = null;
		}
	});

}

/**
 * Decide whether the authority rejects one of the codes.
 *
 * Only a first submission is eligible. A retry follows a freshly generated OTP,
 * so re-arming the failure there would make the register impossible to recover —
 * which is the opposite of what the recovery screen promises.
 */
function applyFailureMode(d: MockState, registerIds: string[]) {
	if (d.failureMode !== "one_otp_expired") return;
	const victim = registerIds[Math.min(2, registerIds.length - 1)];
	if (victim) d.failing[victim] = "compliance";
}

function hashOf(value: string): number {
	let h = 0;
	for (const ch of value) h = (h * 31 + ch.charCodeAt(0)) | 0;
	return h;
}

export async function submitOtp(input: SubmitOtpInput): Promise<Setup> {
	await writeDelay();
	const setup = db.read().setup;
	requireDraft(setup);

	if (!setup.acknowledged) {
		throw new ApiError("api.fixHighlighted", {
			fieldErrors: [{ field: "acknowledged", key: "validation.required" }],
		});
	}

	/**
	 * Phase 1 asks for no codes.
	 *
	 * Nothing is transmitted to the authority and no certificate is issued, so
	 * there is no exchange to authorise and nothing to wait for: the setup is
	 * complete the moment it is submitted.
	 */
	if (setup.phase === "phase_1") {
		return clone(
			db.write((d) => {
				const now = new Date().toISOString();
				d.setup.reference ??= `SETUP-${Math.abs(hashOf(d.setup.id + now)).toString(16).toUpperCase().slice(0, 4)}`;
				d.setup.startedAt = now;
				d.setup.completedAt = now;
				d.setup.status = "live";
				d.setup.registers = d.setup.registers.map((r) => ({ ...r, status: "live" }));
				d.setup.step = "done";
			}).setup,
		);
	}

	const errors = input.entries.flatMap((entry) => {
		const problem = otpProblem(entry.code);
		return problem ? [{ field: entry.registerId, key: problem.key, params: problem.params }] : [];
	});
	const missing = setup.registers.filter(
		(r) => !input.entries.some((e) => e.registerId === r.id && e.code.length === 6),
	);
	if (errors.length || missing.length) {
		throw new ApiError("api.otpAll", { fieldErrors: errors });
	}

	return clone(
		db.write((d) => {
			for (const entry of input.entries) d.otp[entry.registerId] = entry.code;
			const ids = d.setup.registers.map((r) => r.id);
			beginRun(d, ids);
			applyFailureMode(d, ids);
			tick(d);
		}).setup,
	);
}

export async function retryRegisters(ids: string[], _entries: OtpEntry[] = []): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			const targets = d.setup.registers.filter((r) => ids.includes(r.id) && r.status === "failed");
			if (!targets.length) throw new ApiError("api.nothingToRetry", { status: 409 });
			// a retry follows a freshly generated code, so the previous failure is cleared
			for (const r of targets) delete d.failing[r.id];
			d.setup.completedAt = null;
			beginRun(
				d,
				targets.map((r) => r.id),
			);
			tick(d);
		}).setup,
	);
}

/** Accept the run as it stands, leaving any failed register in draft. */
export async function finishWithLive(): Promise<Setup> {
	await writeDelay();
	return clone(
		db.write((d) => {
			tick(d);
			if (d.setup.status === "running") {
				throw new ApiError("api.stillRunning", { status: 409 });
			}
			d.setup.completedAt = new Date().toISOString();
			d.setup.step = "done";
		}).setup,
	);
}

/* ── The log ────────────────────────────────────────────────────────────── */

const DOCUMENTS = [
	"standard invoice",
	"standard credit note",
	"standard debit note",
	"simplified invoice",
	"simplified credit note",
	"simplified debit note",
];

/**
 * The exchanges behind one register.
 *
 * Derived from where the run got to, so the log agrees with the progress board
 * rather than telling a second story: every stage the register cleared appears
 * as a call that succeeded, and a stage that failed appears as the authority
 * refusing one specific document.
 */
export async function getRegisterLog(register: string, limit = 100): Promise<LogEntry[]> {
	await readDelay();

	const target = db.read().setup.registers.find((r) => r.id === register);
	if (!target) throw new ApiError("api.registerGone", { status: 404 });

	const run = target.run;
	if (!run) return [];

	const started = Date.parse(db.read().setup.startedAt ?? new Date().toISOString());
	const entries: LogEntry[] = [];
	let clock = started;

	const push = (operation: string, outcome: LogOutcome, durationMs: number, extra?: Partial<LogEntry>) => {
		clock += durationMs + 120;
		entries.push({
			id: `LOG-${entries.length + 1}`,
			at: new Date(clock).toISOString(),
			environment: "sandbox",
			operation,
			outcome,
			httpStatus: outcome === "ok" ? 200 : outcome === "rejected" ? 400 : null,
			durationMs,
			message: null,
			...extra,
		});
	};

	if (run.stages.csr !== "idle") {
		push("certificate request", run.stages.csr === "fail" ? "rejected" : "ok", 640);
	}
	if (run.stages.compliance !== "idle") {
		const failed = run.stages.compliance === "fail";
		push("compliance certificate", failed ? "rejected" : "ok", 910, {
			message: failed ? "The submitted OTP is no longer valid for this register." : null,
		});
	}
	if (run.stages.tests !== "idle") {
		// each of the six documents is its own call, which is the whole point of
		// having a log: one of them fails and the operator needs to know which
		const reached = run.stages.tests === "done" ? 6 : (run.testInvoice ?? 1);
		for (let i = 0; i < reached; i++) {
			const last = i === reached - 1;
			const failed = last && run.stages.tests === "fail";
			push(`compliance document · ${DOCUMENTS[i]}`, failed ? "rejected" : "ok", 380 + i * 40, {
				message: failed ? `BR-KSA-44: ${DOCUMENTS[i]} rejected — tax total does not match the sum of line taxes.` : null,
			});
		}
	}
	if (run.stages.production !== "idle") {
		push("production certificate", run.stages.production === "fail" ? "error" : "ok", 720);
	}

	return entries.reverse().slice(0, limit);
}

/* ── Dev scenarios ──────────────────────────────────────────────────────── */

export type ScenarioName =
	| "fresh"
	| "single_draft"
	| "multi_draft"
	| "ready_to_review"
	| "awaiting_otp"
	| "running"
	| "partial_failure"
	| "live";

function seededSetup(registerCount: number, expected: number | null): Setup {
	const s = emptySetup(COMPANIES[0].name);
	s.status = "draft";
	s.phase = "phase_2";
	s.scope = expected === 1 ? "single" : "multiple";
	s.expectedRegisters = expected;
	s.entity = {
		company: COMPANIES[0].name,
		legalNameAr: COMPANIES[0].defaultLegalNameAr,
		tin: "300123456789003",
	};
	s.registers = reindex(
		DEMO_REGISTERS.slice(0, registerCount).map((r, i) =>
			buildRegister(`REG-${String(i + 1).padStart(4, "0")}`, i + 1, r),
		),
	);
	return s;
}

export async function applyScenario(name: ScenarioName): Promise<Setup> {
	await writeDelay();
	db.reset();

	return clone(
		db.write((d) => {
			switch (name) {
				case "fresh":
					break;
				case "single_draft":
					d.setup = seededSetup(1, 1);
					break;
				case "multi_draft":
					d.setup = seededSetup(3, 5);
					break;
				case "ready_to_review":
					d.setup = seededSetup(5, 5);
					break;
				case "awaiting_otp":
					d.setup = seededSetup(5, 5);
					d.setup.acknowledged = true;
					break;
				case "running": {
					d.setup = seededSetup(5, 5);
					d.setup.acknowledged = true;
					beginRun(
						d,
						d.setup.registers.map((r) => r.id),
					);
					break;
				}
				case "partial_failure": {
					d.setup = seededSetup(5, 5);
					d.setup.acknowledged = true;
					d.failureMode = "one_otp_expired";
					const ids = d.setup.registers.map((r) => r.id);
					beginRun(d, ids);
					applyFailureMode(d, ids);
					// rewind the clock so the run has already finished
					rewind(d);
					break;
				}
				case "live": {
					d.setup = seededSetup(5, 5);
					d.setup.acknowledged = true;
					beginRun(
						d,
						d.setup.registers.map((r) => r.id),
					);
					rewind(d);
					break;
				}
			}
			tick(d);
		}).setup,
	);
}

/** Shift every start time into the past so the run reads as already finished. */
function rewind(d: MockState) {
	const back = runDurationMs(d.setup.registers, d.speed) + 2000;
	const shift = (iso: string) => new Date(Date.parse(iso) - back).toISOString();
	d.setup.startedAt = d.setup.startedAt ? shift(d.setup.startedAt) : null;
	for (const id of Object.keys(d.runStartedAt)) d.runStartedAt[id] = shift(d.runStartedAt[id]);
}

export async function setSpeed(speed: number): Promise<Setup> {
	return clone(
		db.write((d) => {
			d.speed = speed;
		}).setup,
	);
}

export async function setFailureMode(mode: MockState["failureMode"]): Promise<Setup> {
	return clone(
		db.write((d) => {
			d.failureMode = mode;
		}).setup,
	);
}

/** The mock serves one company, so scoping it is a no-op. */
/**
 * The stand-in holds one setup, so scoping it changes nothing it can serve — but
 * the guards ask which company is chosen, and answering honestly is what lets
 * the company screen behave here the way it does against a bench.
 */
export { scopedCompany, setCompanyScope } from "../scope";

export function readDevState(): { speed: number; failureMode: MockState["failureMode"] } {
	const d = db.read();
	return { speed: d.speed, failureMode: d.failureMode };
}
