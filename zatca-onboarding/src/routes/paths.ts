import type { Setup, SetupStep } from "@/api";

/** Every URL in the app, and the wizard order the guard enforces. */
export const paths = {
	root: "/",
	welcome: "/setup",
	howItWorks: "/setup/how-it-works",
	company: "/setup/company",
	mode: "/setup/mode",
	scope: "/setup/scope",
	entity: "/setup/entity",
	registers: "/setup/registers",
	review: "/setup/review",
	otp: "/setup/otp",
	progress: "/setup/progress",
	done: "/setup/done",
	// relative to the router's basename, which is `/zatca-onboarding` when Frappe
	// serves the build; repeating the prefix here would double it
	log: "/log",
	registerAdmin: "/registers",
} as const;

/** Wizard steps in the order they are completed. */
export const STEP_ORDER: SetupStep[] = [
	"mode",
	"scope",
	"entity",
	"registers",
	"review",
	"otp",
	"progress",
	"done",
];

export const stepPath: Record<SetupStep, string> = {
	mode: paths.mode,
	scope: paths.scope,
	entity: paths.entity,
	registers: paths.registers,
	review: paths.review,
	otp: paths.otp,
	progress: paths.progress,
	done: paths.done,
};

/**
 * The step to show, which is not always the step the server names.
 *
 * Phase 1 puts a QR code on the printed invoice and transmits nothing: no
 * certificate is issued, so there is nothing a one-time password could
 * authorise. The server still reports `otp` as the next thing to do — it is
 * where the submission happens — but for phase 1 that submission is made from
 * the review page with no codes at all.
 */
export function effectiveStep(s: Setup): SetupStep {
	if (s.step === "otp" && s.phase === "phase_1") return "review";
	return s.step;
}

/** Phase 1 has nothing to authorise, so the OTP screen does not exist for it. */
export const needsOtp = (s: Setup): boolean => s.phase !== "phase_1";

/**
 * May this step be opened, given what has actually been filled in?
 *
 * Stated as one precondition per step rather than an ordinal comparison, because
 * the rules are not a simple prefix: the review page is reachable as soon as one
 * register exists, even while the operator is still adding more.
 *
 * The step the server itself named is always admitted. The two derivations agree
 * in every ordinary state, but the server is the authority on where the operator
 * is, and a state it considers current that this function considers unreachable
 * would redirect to itself forever — a blank, spinning page. Deferring to it
 * makes that impossible by construction rather than by matching rules that live
 * in two codebases.
 */
export function canReach(step: SetupStep, s: Setup): boolean {
	// Once the authority has issued certificates, the wizard is a record of what
	// happened, not a form. Every earlier step would render an editable version of
	// a decision that is already binding — and the server refuses those writes
	// anyway, so the only thing a pasted URL could produce is a form that cannot
	// be saved. There is nothing behind these screens any more.
	//
	// The exception is a run that was accepted with registers still outstanding.
	// The done screen offers to finish them, and the only control that can — the
	// retry — lives on the progress board. Without this the button navigated to a
	// step the guard immediately bounced back to done, so it did nothing at all.
	if (s.completedAt) return step === "done" || (step === "progress" && s.status === "partial");

	// While a run is in flight the decisions behind it are equally settled: the
	// certificates being issued are for the registers as they stand.
	if (s.status === "running" || s.status === "partial") return step === "progress";

	if (step === "otp" && !needsOtp(s)) return false;
	if (step === effectiveStep(s)) return true;

	switch (step) {
		case "mode":
			return true;
		case "scope":
			return Boolean(s.phase);
		case "entity":
			return Boolean(s.scope);
		case "registers":
			return Boolean(s.entity);
		case "review":
			return s.registers.length > 0;
		case "otp":
			return s.registers.length > 0 && s.acknowledged;
		case "progress":
			return Boolean(s.startedAt);
		case "done":
			return Boolean(s.completedAt);
	}
}
