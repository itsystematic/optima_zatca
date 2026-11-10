import { describe, expect, it } from "vitest";
import { connectable, connectionStatus, detailsLocked, groupByRegister } from "@/environments";
import type { Environment, RegisteredRow } from "@/types";

function row(crn: string, environment: Environment, flags: Partial<RegisteredRow> = {}): RegisteredRow {
	return {
		company: "Optima Trading Co",
		company_name_in_arabic: "شركة أوبتيما للتجارة",
		tax_id: "310122393500003",
		commercial_register_number: crn,
		commercial_register_name: `CR ${crn}`,
		short_address: "RRRD2929",
		building_no: "2929",
		address_line1: "King Fahd Road",
		address_line2: "1234",
		city: "Riyadh",
		pincode: "12211",
		district: "Al Olaya",
		otp: "",
		phase: "Phase Two",
		setting: `Optima Trading Co-${crn}`,
		environment,
		check_csid: 0,
		check_pcsid: 0,
		use_for_invoices: 0,
		...flags,
	};
}

describe("connectionStatus", () => {
	it("reads the certificate flags", () => {
		expect(connectionStatus({ check_csid: 0, check_pcsid: 0 })).toBe("not_connected");
		expect(connectionStatus({ check_csid: 1, check_pcsid: 0 })).toBe("in_progress");
		expect(connectionStatus({ check_csid: 1, check_pcsid: 1 })).toBe("connected");
	});
});

describe("groupByRegister", () => {
	it("gives each register one entry, production first, in the order registers first appear", () => {
		const groups = groupByRegister([
			row("2", "simulation", { check_csid: 1, check_pcsid: 1, use_for_invoices: 1 }),
			row("1", "production", { check_csid: 1, check_pcsid: 1, use_for_invoices: 1 }),
			row("2", "production", { check_csid: 1 }),
		]);
		expect(groups.map((g) => g.register.commercial_register_number)).toEqual(["2", "1"]);
		expect(groups[0].connections).toEqual([
			{ environment: "production", status: "in_progress", usedForInvoices: false },
			{ environment: "simulation", status: "connected", usedForInvoices: true },
		]);
	});
});

describe("connectable", () => {
	const offered: Environment[] = ["simulation", "production"];

	it("offers the environments not connected yet, including one to resume", () => {
		const [group] = groupByRegister([row("1", "simulation", { check_csid: 1, check_pcsid: 1 }), row("1", "production", { check_csid: 1 })]);
		expect(connectable(group, offered)).toEqual(["production"]);
	});

	it("offers nothing once every offered environment is connected", () => {
		const [group] = groupByRegister([
			row("1", "simulation", { check_csid: 1, check_pcsid: 1 }),
			row("1", "production", { check_csid: 1, check_pcsid: 1 }),
		]);
		expect(connectable(group, offered)).toEqual([]);
	});

	it("never offers sandbox unless the site does", () => {
		const [group] = groupByRegister([row("1", "production", { check_csid: 1, check_pcsid: 1 })]);
		expect(connectable(group, offered)).toEqual(["simulation"]);
		expect(connectable(group, ["sandbox", ...offered])).toEqual(["simulation", "sandbox"]);
	});
});

describe("detailsLocked", () => {
	it("locks the details once any environment holds a compliance CSID", () => {
		expect(detailsLocked(groupByRegister([row("1", "production")])[0])).toBe(false);
		expect(detailsLocked(groupByRegister([row("1", "production"), row("1", "simulation", { check_csid: 1 })])[0])).toBe(true);
	});
});
