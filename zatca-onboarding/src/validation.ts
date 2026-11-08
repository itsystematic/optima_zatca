import type { CommercialRegister, RegisterField } from "@/types";

/**
 * Field rules, carried over from the v15 wizard (src/constants/index.ts) with
 * the length limits validate_address enforces on the server. Messages are
 * source strings; the screen translates them.
 */
export interface FieldSpec {
	key: RegisterField;
	label: string;
	required: boolean;
	message: string;
	pattern?: RegExp;
	maxlength?: number;
	numeric?: boolean;
}

export const TAX_ID = /^3\d{13}3$/;
export const OTP = /^\d{6}$/;
export const OTP_LENGTH = 6;

export const REGISTER_FIELDS: FieldSpec[] = [
	{
		key: "commercial_register_name",
		label: "CR name",
		required: true,
		message: "CR name is required",
	},
	{
		key: "commercial_register_number",
		label: "CRN",
		required: true,
		pattern: /^\d{10}$/,
		maxlength: 10,
		numeric: true,
		message: "CRN must be 10 digits",
	},
];

/** Split into the two columns of the address grid. */
export const ADDRESS_COLUMNS: FieldSpec[][] = [
	[
		{
			key: "short_address",
			label: "Short address",
			required: true,
			maxlength: 8,
			message: "Short address is required",
		},
		{
			key: "building_no",
			label: "Building no",
			required: true,
			pattern: /^\d{4}$/,
			maxlength: 4,
			numeric: true,
			message: "Building no must be 4 digits",
		},
		{
			key: "address_line1",
			label: "Street",
			required: true,
			maxlength: 1000,
			message: "Street is required",
		},
		{
			key: "address_line2",
			label: "Secondary no",
			required: true,
			message: "Secondary no is required",
		},
	],
	[
		{ key: "city", label: "City", required: true, maxlength: 100, message: "City is required" },
		{
			key: "district",
			label: "District",
			required: true,
			maxlength: 127,
			message: "District is required",
		},
		{
			key: "pincode",
			label: "Postal code",
			required: true,
			pattern: /^\d{5}$/,
			maxlength: 5,
			numeric: true,
			message: "Postal code must be 5 digits",
		},
		{ key: "more_info", label: "More info", required: false, message: "" },
	],
];

const ALL_FIELDS = [...REGISTER_FIELDS, ...ADDRESS_COLUMNS.flat()];

export type Errors<K extends string> = Partial<Record<K, string>>;

export function fieldError(spec: FieldSpec, value: string): string | undefined {
	const v = value.trim();
	if (!v) return spec.required ? spec.message : undefined;
	if (spec.pattern && !spec.pattern.test(v)) return spec.message;
	return undefined;
}

/** `taken` lists the CRNs already live and those already in this draft (minus the one being edited). */
export function validateRegister(
	register: CommercialRegister,
	taken: { registered: string[]; added: string[] } = { registered: [], added: [] },
): Errors<RegisterField> {
	const errors: Errors<RegisterField> = {};
	for (const spec of ALL_FIELDS) {
		const error = fieldError(spec, register[spec.key] ?? "");
		if (error) errors[spec.key] = error;
	}
	const crn = register.commercial_register_number.trim();
	if (!errors.commercial_register_number) {
		if (taken.registered.includes(crn)) errors.commercial_register_number = "This CRN is already registered";
		else if (taken.added.includes(crn)) errors.commercial_register_number = "This CRN is already added";
	}
	return errors;
}

export type CompanyField = "company" | "company_name_in_arabic" | "tax_id";

export function validateCompany(values: Record<CompanyField, string>): Errors<CompanyField> {
	const errors: Errors<CompanyField> = {};
	if (!values.company.trim()) errors.company = "Select a company";
	if (!values.company_name_in_arabic.trim()) {
		errors.company_name_in_arabic = "Company name in Arabic is required";
	}
	if (!TAX_ID.test(values.tax_id.trim())) {
		errors.tax_id = "VAT number must be 15 digits, starting and ending with 3";
	}
	return errors;
}

export function otpError(otp: string): string | undefined {
	return OTP.test(otp.trim()) ? undefined : "OTP must be 6 digits";
}

export function isClean(errors: object): boolean {
	return Object.keys(errors).length === 0;
}

export function normalizeRegister(register: CommercialRegister): CommercialRegister {
	return Object.fromEntries(
		Object.entries(register).map(([k, v]) => [k, String(v ?? "").trim()]),
	) as unknown as CommercialRegister;
}
