import { computed, reactive } from "vue";
import { registerCompany, subscribeZatca } from "@/api";
import { loadRegistered } from "@/registered";
import {
	applyEvent,
	failRequest,
	initialRow,
	startAttempt,
	summarize,
	withImpliedRunning,
	type RowProgress,
} from "@/progress";
import type { CommercialRegister, RegisterPayload } from "@/types";
import { resetDraft } from "@/wizard";

/** The registers being onboarded, and what the "zatca" events have said about each. */
export const run = reactive({
	active: false,
	payload: null as RegisterPayload | null,
	rows: {} as Record<string, RowProgress>,
});

let unsubscribe: (() => void) | null = null;

export const board = computed(() => {
	const registers = run.payload?.commercial_register ?? [];
	const rows = withImpliedRunning(registers.map((r) => run.rows[r.commercial_register_number]));
	return registers.map((register, i) => ({ register, progress: rows[i] }));
});

export const totals = computed(() => summarize(board.value.map((r) => r.progress)));

/** Fire, then listen: the board never waits for register_company to return. */
export function startRun(payload: RegisterPayload) {
	run.active = true;
	run.payload = payload;
	run.rows = Object.fromEntries(payload.commercial_register.map((r) => [r.commercial_register_number, initialRow()]));
	listen();
	fire(payload.commercial_register);
}

export function retry(crn: string, otp?: string) {
	const register = run.payload?.commercial_register.find((r) => r.commercial_register_number === crn);
	if (!register) return;
	if (otp) register.otp = otp;
	run.rows[crn] = startAttempt(run.rows[crn]);
	fire([register]);
}

/** Close the board and forget the draft; resolves once the registered list is fresh. */
export function finishRun() {
	unsubscribe?.();
	unsubscribe = null;
	Object.assign(run, { active: false, payload: null, rows: {} });
	resetDraft();
	return loadRegistered(true);
}

function listen() {
	unsubscribe ??= subscribeZatca((event) => {
		const crn = event.commercial_register_name;
		if (crn && run.rows[crn]) run.rows[crn] = applyEvent(run.rows[crn], event);
	});
}

function fire(registers: CommercialRegister[]) {
	const payload = { ...run.payload!, commercial_register: registers };
	registerCompany(payload).catch((error) => {
		const message = errorText(error);
		for (const r of registers) {
			const crn = r.commercial_register_number;
			run.rows[crn] = failRequest(run.rows[crn], message);
		}
	});
}

/** frappe-ui rejects with the server's messages, which may carry markup such as frappe.bold. */
export function errorText(error: unknown): string {
	const e = error as { messages?: string[]; message?: string };
	const text = e?.messages?.[0] ?? e?.message ?? String(error);
	return text.replace(/<[^>]*>/g, "");
}
