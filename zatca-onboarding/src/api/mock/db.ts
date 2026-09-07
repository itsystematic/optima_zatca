import type { Setup, StageKey } from "../types";
import { COMPANIES, emptySetup } from "./seed";

/**
 * The mock backend's persistence.
 *
 * State lives in `localStorage` so a reload behaves the way it will once this is
 * a real doctype: the wizard resumes, an in-flight run keeps running, and the
 * dev scenarios survive a refresh. Bump `KEY` when the shape changes.
 */

const KEY = "optima_zatca.mock.v1";

export type FailureMode = "none" | "one_otp_expired";

export type MockState = {
	setup: Setup;
	/** speed multiplier for the run simulator: 1 is demo pace, 4 is closer to life */
	speed: number;
	failureMode: FailureMode;
	/** register ids the next run should fail, and where */
	failing: Record<string, StageKey>;
	/** when each register was released to a worker; drives all run progress */
	runStartedAt: Record<string, string>;
	/** attempt counter per register, so a retry reads as attempt 3 of 3 */
	attempts: Record<string, number>;
	/** OTP codes as submitted, kept only so the modal can be revisited */
	otp: Record<string, string>;
};

function fresh(): MockState {
	return {
		setup: emptySetup(COMPANIES[0].name),
		speed: 1,
		failureMode: "none",
		failing: {},
		runStartedAt: {},
		attempts: {},
		otp: {},
	};
}

let state: MockState = load();

function load(): MockState {
	if (typeof localStorage === "undefined") return fresh();
	try {
		const raw = localStorage.getItem(KEY);
		if (!raw) return fresh();
		const parsed = JSON.parse(raw) as MockState;
		// a missing key means an older snapshot; start over rather than guess
		if (!parsed?.setup?.id) return fresh();
		return { ...fresh(), ...parsed };
	} catch {
		return fresh();
	}
}

function persist() {
	if (typeof localStorage === "undefined") return;
	try {
		localStorage.setItem(KEY, JSON.stringify(state));
	} catch {
		// a full or disabled store is not worth failing a request over
	}
}

export const db = {
	read(): MockState {
		return state;
	},

	/** Apply a change and persist it. Returns the new state. */
	write(mutate: (draft: MockState) => void): MockState {
		mutate(state);
		state.setup.modified = new Date().toISOString();
		persist();
		return state;
	},

	replace(next: MockState) {
		state = next;
		persist();
	},

	reset() {
		state = fresh();
		persist();
	},
};
