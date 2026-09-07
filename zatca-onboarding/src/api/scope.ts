/**
 * Which company this tab is setting up.
 *
 * Neither backend's business: it is a browser fact, read by the live transport to
 * address its calls and by the guards to decide whether the operator still owes
 * the wizard a choice. Kept out of `./live` so the mock reports the same answer
 * rather than a no-op, and so nothing has to import the live module to ask.
 */

const SCOPE_KEY = "optima_zatca.company";

/**
 * Which company this session is setting up.
 *
 * Omitted, the server uses the operator's default company, or the only one on
 * the site. `?company=…` overrides that, which is how a desk link points at a
 * particular company on a site that has several — without it every company but
 * the default is unreachable.
 *
 * The choice is held for the tab rather than read from the current URL: the
 * router drops query parameters as it navigates, and a half-kept scope would
 * silently move the operator to a different company mid-flow. An empty
 * `?company=` clears it and hands control back to the server's default.
 */
export function scopedCompany(): string | undefined {
	if (typeof window === "undefined") return undefined;

	const requested = new URLSearchParams(window.location.search).get("company");
	if (requested !== null) {
		if (requested) sessionStorage.setItem(SCOPE_KEY, requested);
		else sessionStorage.removeItem(SCOPE_KEY);
	}

	return sessionStorage.getItem(SCOPE_KEY) ?? undefined;
}

/**
 * Point this tab at a different company.
 *
 * The server keys a setup by company, so this changes which record every
 * subsequent call reads and writes. Callers must refetch afterwards: the record
 * in hand belongs to the company they just left.
 */
export function setCompanyScope(company: string | null) {
	if (typeof window === "undefined") return;
	if (company) sessionStorage.setItem(SCOPE_KEY, company);
	else sessionStorage.removeItem(SCOPE_KEY);
}
