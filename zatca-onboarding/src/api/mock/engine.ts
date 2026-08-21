import { STAGE_KEYS } from "../types";
import type { Certificate, Register, RegisterRun, RunError, StageKey, StageState } from "../types";

/**
 * The registration simulator.
 *
 * Progress is a pure function of elapsed wall-clock time rather than a set of
 * timers: `runFor()` is called on every poll and derives the whole state from
 * `startedAt`. That means a reload mid-run resumes exactly where it left off,
 * and nothing drifts if the tab is backgrounded — the same properties the real
 * backend has, where progress lives in the database and not in the browser.
 */

/** Milliseconds each stage takes at speed 1. */
const DURATION: Record<StageKey, number> = {
	keys: 1800,
	csr: 2600,
	compliance: 3200,
	tests: 5400,
	production: 2400,
};

/** Six documents go out across the test stage, and the UI counts them. */
const TEST_DOCUMENTS = 6;

/** Registers do not all start at once; the queue releases one every so often. */
export const STAGGER_MS = 900;

/** Small deterministic per-register variation so rows do not move in lockstep. */
function jitter(seed: string): number {
	let h = 0;
	for (const ch of seed) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
	return 0.85 + (h % 40) / 100; // 0.85 – 1.24
}

function idleStages(): Record<StageKey, StageState> {
	return { keys: "idle", csr: "idle", compliance: "idle", tests: "idle", production: "idle" };
}

export type RunOutcome = {
	status: Register["status"];
	run: RegisterRun;
	certificate: Certificate | null;
};

/**
 * Where one register stands `elapsedMs` after the run started.
 *
 * `failAt` names the stage the authority rejects, if this register is the one
 * the scenario fails. `attempt` feeds the retry counter in the error panel.
 */
export function runFor(opts: {
	register: Register;
	elapsedMs: number;
	speed: number;
	failAt?: StageKey | null;
	attempt?: number;
	startedAt: string;
}): RunOutcome {
	const { register, speed, failAt, startedAt } = opts;
	const scale = jitter(register.crn) * speed;
	const elapsed = opts.elapsedMs;

	if (elapsed <= 0) {
		return {
			status: "queued",
			run: {
				stages: idleStages(),
				stageProgress: 0,
				stage: STAGE_KEYS[0],
				stageIndex: 1,
				elapsedSeconds: 0,
				error: null,
			},
			certificate: null,
		};
	}

	const stages = idleStages();
	let cursor = 0;

	for (const [i, key] of STAGE_KEYS.entries()) {
		const duration = DURATION[key] * scale;
		const into = elapsed - cursor;
		// the authority rejects part-way through the stage, and it stays rejected:
		// this is checked before the "still running" test so the state is terminal
		const failPoint = duration * 0.7;

		if (failAt === key && into >= failPoint) {
			stages[key] = "fail";
			return {
				status: "failed",
				run: {
					stages,
					stageProgress: 0,
					stage: key,
					stageIndex: i + 1,
					elapsedSeconds: (cursor + failPoint) / 1000,
					error: otpExpiredError(register, opts.attempt ?? 2, startedAt),
				},
				certificate: null,
			};
		}

		if (into < duration) {
			const fraction = Math.max(0, into / duration);
			stages[key] = "run";
			return {
				status: "running",
				run: {
					stages,
					stageProgress: Math.round(fraction * 100),
					stage: key,
					stageIndex: i + 1,
					testInvoice:
						key === "tests"
							? Math.min(TEST_DOCUMENTS, Math.floor(fraction * TEST_DOCUMENTS) + 1)
							: undefined,
					elapsedSeconds: elapsed / 1000,
					error: null,
				},
				certificate: null,
			};
		}

		stages[key] = "done";
		cursor += duration;
	}

	// every stage cleared
	return {
		status: "live",
		run: {
			stages,
			stageProgress: 0,
			stage: STAGE_KEYS[STAGE_KEYS.length - 1],
			stageIndex: STAGE_KEYS.length,
			elapsedSeconds: cursor / 1000,
			error: null,
		},
		certificate: certificateFor(register, startedAt),
	};
}

/** Total simulated milliseconds for a whole run, used to know when to stop polling. */
export function runDurationMs(registers: Register[], speed: number): number {
	let longest = 0;
	registers.forEach((r, i) => {
		const scale = jitter(r.crn) * speed;
		const total = STAGE_KEYS.reduce((sum, k) => sum + DURATION[k] * scale, 0);
		longest = Math.max(longest, total + i * STAGGER_MS * speed);
	});
	return longest;
}

function hex(seed: string, length: number): string {
	let h = 0;
	for (const ch of seed) h = (h * 33 + ch.charCodeAt(0)) >>> 0;
	let out = "";
	while (out.length < length) {
		h = (h * 1103515245 + 12345) >>> 0;
		out += h.toString(16).padStart(8, "0");
	}
	return out.slice(0, length);
}

function certificateFor(register: Register, startedAt: string): Certificate {
	const raw = hex(register.crn, 16);
	const issued = new Date(startedAt);
	const validTo = new Date(issued);
	validTo.setFullYear(validTo.getFullYear() + 2);
	return {
		fingerprint: (raw.match(/.{2}/g) ?? []).join(":"),
		issuedAt: issued.toISOString(),
		validTo: validTo.toISOString(),
	};
}

function otpExpiredError(register: Register, attempt: number, startedAt: string): RunError {
	return {
		code: "otp_expired",
		httpStatus: 400,
		endpoint: "POST /compliance/csr",
		requestId: (hex(register.crn + "req", 16).match(/.{4}/g) ?? []).join("-"),
		attempt,
		maxAttempts: 3,
		occurredAt: startedAt,
		details: {
			message: `"The submitted OTP is no longer valid for CRN ${register.crn}."`,
			otp_age: "71 min (limit 60)",
		},
	};
}
