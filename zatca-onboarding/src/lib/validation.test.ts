import { describe, expect, it } from "vitest";
import {
	crnProblem,
	isValidTin,
	legalNameArProblem,
	otpProblem,
	tinProblem,
	validateRegister,
} from "./validation";

/**
 * Rules are asserted by the key they raise, not by the sentence — the sentence
 * is a translation and belongs to the catalogue, not to the rule.
 */

describe("tax identification number", () => {
	it("accepts 15 digits that open and close with 3", () => {
		expect(isValidTin("300123456789003")).toBe(true);
		expect(tinProblem("300123456789003")).toBeNull();
	});

	it("counts how many digits are missing", () => {
		expect(tinProblem("3001234567890")).toEqual({
			key: "validation.tin.short",
			params: { count: 2, length: 15 },
		});
		expect(tinProblem("30012345678900")?.params).toMatchObject({ count: 1 });
	});

	it("rejects a full-length number that does not bracket with 3", () => {
		expect(isValidTin("100123456789001")).toBe(false);
		expect(tinProblem("100123456789001")?.key).toBe("validation.tin.brackets");
	});

	it("rejects one that is too long", () => {
		expect(tinProblem("3001234567890033")?.key).toBe("validation.tin.long");
	});
});

describe("commercial register number", () => {
	it("wants exactly ten digits", () => {
		expect(crnProblem("1010512345")).toBeNull();
		expect(crnProblem("101051234")?.key).toBe("validation.crn.length");
		expect(crnProblem("10105123456")?.key).toBe("validation.crn.length");
	});
});

describe("Arabic legal name", () => {
	it("requires Arabic script, not a transliteration", () => {
		expect(legalNameArProblem("مصنع قنديل للزجاج المحدودة")).toBeNull();
		expect(legalNameArProblem("Kandil Glass")?.key).toBe("validation.legalName.arabic");
		expect(legalNameArProblem("   ")?.key).toBe("validation.legalName.required");
	});
});

describe("OTP", () => {
	it("is six digits", () => {
		expect(otpProblem("482913")).toBeNull();
		expect(otpProblem("4829")).toEqual({ key: "validation.otp.length", params: { count: 6 } });
	});
});

describe("register", () => {
	const complete = {
		registerName: "Riyadh — Head office",
		crn: "1010512345",
		address: {
			buildingNumber: "8734",
			street: "King Fahd Road",
			district: "Al Olaya",
			city: "Riyadh",
			postalCode: "12211",
			additionalNumber: "",
			vatGroupNumber: "",
			country: "Saudi Arabia",
		},
	};

	it("passes a fully filled register", () => {
		expect(validateRegister(complete)).toEqual([]);
	});

	it("rejects a register number already used in this setup", () => {
		expect(validateRegister(complete, { takenCrns: ["1010512345"] })).toContainEqual({
			field: "crn",
			key: "validation.crn.duplicate",
			params: undefined,
		});
	});

	it("names every missing field at once, not just the first", () => {
		const fields = validateRegister({ registerName: "", crn: "123", address: {} }).map(
			(e) => e.field,
		);
		expect(fields).toEqual(
			expect.arrayContaining([
				"registerName",
				"crn",
				"buildingNumber",
				"street",
				"district",
				"city",
				"postalCode",
			]),
		);
	});

	it("treats the optional numbers as optional but still format-checked", () => {
		expect(
			validateRegister({ ...complete, address: { ...complete.address, additionalNumber: "" } }),
		).toEqual([]);
		expect(
			validateRegister({ ...complete, address: { ...complete.address, additionalNumber: "12" } }),
		).toContainEqual({ field: "additionalNumber", key: "validation.additional.format", params: undefined });
	});
});
