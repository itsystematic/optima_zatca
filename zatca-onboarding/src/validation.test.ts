import { describe, expect, it } from "vitest";
import type { CommercialRegister } from "@/types";
import { otpError, validateCompany, validateRegister } from "@/validation";

const register = (overrides: Partial<CommercialRegister> = {}): CommercialRegister => ({
	commercial_register_name: "Riyadh HQ",
	commercial_register_number: "1010000001",
	short_address: "RRRD2929",
	building_no: "2929",
	address_line1: "King Fahd Road",
	address_line2: "1234",
	city: "Riyadh",
	district: "Al Olaya",
	pincode: "12211",
	otp: "",
	more_info: "",
	...overrides,
});

describe("validateCompany", () => {
	const company = { company: "Optima", company_name_in_arabic: "أوبتيما", tax_id: "300000000000003" };

	it("accepts a 15-digit VAT number that starts and ends with 3", () => {
		expect(validateCompany(company)).toEqual({});
	});

	it.each(["300000000000004", "30000000000003", "400000000000003", "3000000000000a3"])(
		"rejects VAT number %s",
		(tax_id) => {
			expect(validateCompany({ ...company, tax_id }).tax_id).toBeTruthy();
		},
	);
});

describe("validateRegister", () => {
	it("accepts a complete register with no more info", () => {
		expect(validateRegister(register())).toEqual({});
	});

	it("enforces the fixed-length numbers", () => {
		const errors = validateRegister(
			register({ commercial_register_number: "101000000", building_no: "292", pincode: "1221a" }),
		);
		expect(Object.keys(errors).sort()).toEqual(["building_no", "commercial_register_number", "pincode"]);
	});

	it("names whether a clashing CRN is already live or already in the draft", () => {
		const crn = "1010000001";
		expect(validateRegister(register(), { registered: [crn], added: [] }).commercial_register_number).toBe(
			"This CRN is already registered",
		);
		expect(validateRegister(register(), { registered: [], added: [crn] }).commercial_register_number).toBe(
			"This CRN is already added",
		);
	});

	it("ignores surrounding whitespace", () => {
		expect(validateRegister(register({ commercial_register_number: " 1010000001 " }))).toEqual({});
	});
});

describe("otpError", () => {
	it("wants exactly six digits", () => {
		expect(otpError("123456")).toBeUndefined();
		expect(otpError("12345")).toBeTruthy();
		expect(otpError("12345a")).toBeTruthy();
	});
});
