import type { FieldError, MessageParams, Problem, RegisterInput, SaveEntityInput } from "@/api/types";

/**
 * The mandate's field rules, in one place.
 *
 * Rules return a message *key* and its parameters rather than a sentence, so the
 * same rule serves both languages and the mock backend can reject a write
 * without knowing which locale the operator is reading in — exactly how a Frappe
 * method returning a translatable message behaves.
 */

const ARABIC = /[؀-ۿݐ-ݿ]/;
const DIGITS_ONLY = /^\d*$/;

export const TIN_LENGTH = 15;
export const CRN_LENGTH = 10;
export const OTP_LENGTH = 6;
export const BUILDING_LENGTH = 4;
export const POSTAL_LENGTH = 5;

export const digitsOnly = (value: string) => value.replace(/\D/g, "");

export const hasArabicScript = (value: string) => ARABIC.test(value);

const problem = (key: string, params?: MessageParams): Problem => ({ key, params });

/** `true` once the value is a complete, well-formed TIN. */
export function isValidTin(value: string): boolean {
	return new RegExp(`^3\\d{${TIN_LENGTH - 2}}3$`).test(value);
}

export function tinProblem(value: string): Problem {
	if (!value) return problem("validation.tin.required");
	if (!DIGITS_ONLY.test(value)) return problem("validation.digitsOnly");
	if (value.length < TIN_LENGTH) {
		return problem("validation.tin.short", { count: TIN_LENGTH - value.length, length: TIN_LENGTH });
	}
	if (value.length > TIN_LENGTH) return problem("validation.tin.long", { length: TIN_LENGTH });
	if (!isValidTin(value)) return problem("validation.tin.brackets");
	return null;
}

export function crnProblem(value: string): Problem {
	if (!value) return problem("validation.crn.required", { count: CRN_LENGTH });
	if (!DIGITS_ONLY.test(value)) return problem("validation.digitsOnly");
	if (value.length !== CRN_LENGTH) return problem("validation.crn.length", { count: CRN_LENGTH });
	return null;
}

export function legalNameArProblem(value: string): Problem {
	const trimmed = value.trim();
	if (!trimmed) return problem("validation.legalName.required");
	if (!hasArabicScript(trimmed)) return problem("validation.legalName.arabic");
	return null;
}

export function registerNameProblem(value: string): Problem {
	return value.trim() ? null : problem("validation.registerName.required");
}

/** Field rules for the address grid, keyed by the input name. */
export const ADDRESS_RULES: Record<string, (value: string) => Problem> = {
	buildingNumber: (v) =>
		!v
			? problem("validation.required")
			: /^\d{4}$/.test(v)
				? null
				: problem("validation.building.format"),
	street: (v) => (v.trim() ? null : problem("validation.required")),
	district: (v) => (v.trim() ? null : problem("validation.required")),
	city: (v) => (v.trim() ? null : problem("validation.required")),
	postalCode: (v) =>
		!v ? problem("validation.required") : /^\d{5}$/.test(v) ? null : problem("validation.postal.format"),
	additionalNumber: (v) => (!v || /^\d{4}$/.test(v) ? null : problem("validation.additional.format")),
	vatGroupNumber: (v) => (!v || /^\d{15}$/.test(v) ? null : problem("validation.vatGroup.format")),
};

const asError = (field: string, p: Problem): FieldError[] =>
	p ? [{ field, key: p.key, params: p.params }] : [];

export function validateEntity(input: Partial<SaveEntityInput>): FieldError[] {
	return [
		...(input.company ? [] : [{ field: "company", key: "validation.company.required" }]),
		...asError("legalNameAr", legalNameArProblem(input.legalNameAr ?? "")),
		...asError("tin", tinProblem(input.tin ?? "")),
	];
}

export function validateRegister(
	input: Partial<RegisterInput>,
	opts: { takenCrns?: string[] } = {},
): FieldError[] {
	const crn = crnProblem(input.crn ?? "");
	const duplicate =
		!crn && opts.takenCrns?.includes(input.crn ?? "") ? problem("validation.crn.duplicate") : null;

	return [
		...asError("registerName", registerNameProblem(input.registerName ?? "")),
		...asError("crn", crn ?? duplicate),
		...Object.entries(ADDRESS_RULES).flatMap(([field, rule]) =>
			asError(field, rule(String(input.address?.[field as keyof typeof input.address] ?? ""))),
		),
	];
}

export function otpProblem(value: string): Problem {
	if (!value) return problem("validation.required");
	if (value.length !== OTP_LENGTH) return problem("validation.otp.length", { count: OTP_LENGTH });
	return null;
}

/** Turn a `FieldError[]` into a lookup the forms can index by field name. */
export function byField(errors: FieldError[]): Record<string, Problem> {
	const map: Record<string, Problem> = {};
	for (const e of errors) map[e.field] ??= { key: e.key, params: e.params };
	return map;
}
