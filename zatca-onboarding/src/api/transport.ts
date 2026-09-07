import { ApiError } from "./types";

/**
 * The wire between this app and Frappe.
 *
 * Whitelisted methods are always called with POST. Several of them write on
 * first touch — `get_setup` creates the setup record — and Frappe refuses writes
 * during a GET, so a "read" here is still a POST.
 */
export async function call<T>(method: string, args?: Record<string, unknown>): Promise<T> {
	let response: Response;
	try {
		response = await fetch(`/api/method/${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
				"X-Frappe-CSRF-Token": csrfToken(),
			},
			body: JSON.stringify(stripUndefined(args ?? {})),
			credentials: "same-origin",
		});
	} catch {
		// the server is unreachable, rather than unhappy
		throw new ApiError("api.unreachable", { status: 0 });
	}

	const payload = await response.json().catch(() => null);

	if (!response.ok) throw toApiError(payload, response.status);
	return payload?.message as T;
}

/**
 * Translate a Frappe failure.
 *
 * `optima_zatca.api` puts its own structured payload on the response as `optima_error`,
 * carrying a message key and the per-field objections. Anything else — a session
 * that expired, a traceback, a proxy in the way — has no key of its own, so it is
 * mapped to one here rather than surfacing raw server prose in the interface.
 */
function toApiError(payload: unknown, status: number): ApiError {
	const body = payload as
		| { optima_error?: { key?: string; fieldErrors?: unknown }; exc_type?: string }
		| null;
	const structured = body?.optima_error;

	if (structured?.key) {
		return new ApiError(structured.key, {
			fieldErrors: Array.isArray(structured.fieldErrors)
				? (structured.fieldErrors as ApiError["fieldErrors"])
				: [],
			status,
		});
	}

	if (status === 401 || body?.exc_type === "AuthenticationError") {
		return new ApiError("api.notSignedIn", { status });
	}
	if (status === 403 || body?.exc_type === "PermissionError") {
		return new ApiError("api.notPermitted", { status });
	}
	return new ApiError("common.somethingWrong", { status });
}

/** Frappe omits `null`/`undefined` arguments; sending them sets fields to null. */
function stripUndefined(args: Record<string, unknown>): Record<string, unknown> {
	return Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined));
}

/**
 * The desk page emits the token into `window.csrf_token`. In the Vite dev server
 * the Jinja expression is never substituted, so an unrendered placeholder is
 * treated as no token at all.
 */
function csrfToken(): string {
	const token = (window as unknown as { csrf_token?: string }).csrf_token ?? "";
	return token.includes("{{") ? "" : token;
}
