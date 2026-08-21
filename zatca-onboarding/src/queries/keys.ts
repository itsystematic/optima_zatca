/** Every cache key in the app, so invalidation never guesses at a string. */
export const qk = {
	setup: ["setup"] as const,
	guidance: ["guidance"] as const,
	companies: ["companies"] as const,
	cities: ["cities"] as const,
	phaseOptions: ["phase-options"] as const,
	registerLog: (register: string, limit?: number) => ["register-log", register, limit] as const,
};

/**
 * Which of those reads answer differently per company.
 *
 * Switching company has to drop exactly these, and a new scoped query that is not
 * listed here would keep serving the previous company's answer. `keys.test.ts`
 * makes forgetting one a failing test rather than a screen showing the wrong
 * company's registers.
 */
export const SCOPED_KEYS = [qk.setup, qk.phaseOptions, ["register-log"]] as const;

/**
 * Reads that answer the same whichever company is chosen, so a switch keeps them
 * rather than dropping them and showing a loading state for nothing.
 *
 * Surviving a switch is not the same as never going stale — see below.
 */
export const GLOBAL_KEYS = [qk.guidance, qk.companies, qk.cities] as const;

/**
 * Reads whose contents change as a setup progresses.
 *
 * The company list carries each company's setup status, which is what the picker
 * renders as "In progress" or "Already registered". It is held indefinitely
 * because every screen's guard reads it, so nothing refetches it on its own —
 * which meant a company registered a moment ago still showed as unregistered
 * until the operator reloaded the page. These are invalidated whenever a setup
 * changes hands or state.
 */
export const SETUP_DERIVED_KEYS = [qk.companies] as const;
