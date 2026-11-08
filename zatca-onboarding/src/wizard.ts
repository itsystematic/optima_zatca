import { reactive, watch } from "vue";
import type { CommercialRegister, Phase, RegisterPayload, RegisterType, RegisteredRow } from "@/types";

/** The v15 DataState, plus the register type it kept in a slice of its own. */
export interface Draft {
	phase: Phase | "";
	register_type: RegisterType | "";
	company: string;
	company_name_in_arabic: string;
	tax_id: string;
	commercial_register: CommercialRegister[];
	/** A return visit: company and phase come from the registers already live. */
	adding: boolean;
}

const STORAGE_KEY = "optima_zatca.onboarding.draft";

function emptyDraft(): Draft {
	return {
		phase: "",
		register_type: "",
		company: "",
		company_name_in_arabic: "",
		tax_id: "",
		commercial_register: [],
		adding: false,
	};
}

function load(): Draft {
	try {
		return { ...emptyDraft(), ...JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "{}") };
	} catch {
		return emptyDraft();
	}
}

export const draft = reactive<Draft>(load());

watch(
	draft,
	(value) => {
		// OTPs are single-use and short-lived; they stay in memory only.
		const stored = { ...value, commercial_register: value.commercial_register.map((r) => ({ ...r, otp: "" })) };
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
	},
	{ deep: true },
);

export function resetDraft() {
	Object.assign(draft, emptyDraft());
}

export function startAdding(existing: RegisteredRow) {
	Object.assign(draft, emptyDraft(), {
		adding: true,
		register_type: "multi",
		phase: existing.phase,
		company: existing.company,
		company_name_in_arabic: existing.company_name_in_arabic,
		tax_id: existing.tax_id,
	});
}

export function emptyRegister(): CommercialRegister {
	return {
		commercial_register_name: "",
		commercial_register_number: "",
		short_address: "",
		building_no: "",
		address_line1: "",
		address_line2: "",
		city: "",
		district: "",
		pincode: "",
		otp: "",
		more_info: "",
	};
}

export function saveRegister(register: CommercialRegister) {
	const i = draft.commercial_register.findIndex(
		(r) => r.commercial_register_number === register.commercial_register_number,
	);
	if (i === -1) draft.commercial_register.push(register);
	else draft.commercial_register.splice(i, 1, register);
}

export function removeRegister(crn: string) {
	draft.commercial_register = draft.commercial_register.filter((r) => r.commercial_register_number !== crn);
}

export function toPayload(d: Draft): RegisterPayload {
	return {
		company: d.company,
		company_name_in_arabic: d.company_name_in_arabic,
		tax_id: d.tax_id,
		phase: d.phase as Phase,
		commercial_register: d.commercial_register.map((r) => ({ ...r })),
	};
}

export type WizardRoute = "phase" | "type" | "company" | "registers" | "review";

/** Sends a deep link or a reload back to the first question still unanswered. */
export function guardRedirect(route: WizardRoute, d: Draft): WizardRoute | null {
	if (d.adding) {
		if (route === "phase" || route === "type" || route === "company") return "registers";
	} else {
		if (route === "phase") return null;
		if (!d.phase) return "phase";
		if (route === "type") return null;
		if (!d.register_type) return "type";
		if (route === "company") return null;
		if (!d.company || !d.company_name_in_arabic || !d.tax_id) return "company";
	}
	if (route === "registers") return null;
	return d.commercial_register.length ? null : "registers";
}
