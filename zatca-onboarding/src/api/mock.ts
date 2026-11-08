/**
 * Stand-in for the v15 backend under `yarn dev:mock`. Same three calls, same
 * payloads, and the same "zatca" events in the same order and percentages as
 * zatca/setup.py and zatca/demo.py, so switching to live.ts changes nothing in
 * the screens.
 *
 *   ?scenario=ok       every register goes live (default)
 *   ?scenario=reject   the last register of the first run has test invoice 4 rejected
 *   ?scenario=otp      the first register of the first run is refused its CSID
 *   ?seed=registered   start as a return visit with two registers already live
 *   ?seed=empty        forget the registers this mock has onboarded
 */
import type { Company, CommercialRegister, RegisterPayload, RegisteredRow, ZatcaEvent } from "@/types";
import { TAX_ID } from "@/validation";

const REGISTERED_KEY = "optima_zatca.mock.registered";
const SCENARIO_KEY = "optima_zatca.mock.scenario";

const params = new URLSearchParams(window.location.search);
if (params.get("scenario")) sessionStorage.setItem(SCENARIO_KEY, params.get("scenario")!);
const scenario = sessionStorage.getItem(SCENARIO_KEY) ?? "ok";

const COMPANIES: Company[] = [
	{ name: "Optima Trading Co", company_name_in_arabic: "شركة أوبتيما للتجارة", tax_id: "310122393500003" },
	{ name: "Riyadh Foods", company_name_in_arabic: "", tax_id: "" },
];

const SAMPLE_INVOICES = [
	["Standard", "normal"],
	["Standard", "debit"],
	["Standard", "credit"],
	["Simplified", "normal"],
	["Simplified", "debit"],
	["Simplified", "credit"],
];

if (params.get("seed") === "empty") localStorage.removeItem(REGISTERED_KEY);
if (params.get("seed") === "registered") {
	localStorage.setItem(
		REGISTERED_KEY,
		JSON.stringify([
			seedRow("Riyadh HQ", "1010000001", "Riyadh", "Al Olaya"),
			seedRow("Jeddah Branch", "4030000002", "Jeddah", "Al Rawdah"),
		]),
	);
}

const listeners = new Set<(event: ZatcaEvent) => void>();
const devices = new Map<string, { csid: boolean; tests: boolean[]; pcsid: boolean }>();
let requests = 0;

export function subscribeZatca(handler: (event: ZatcaEvent) => void): () => void {
	listeners.add(handler);
	return () => {
		listeners.delete(handler);
	};
}

export async function getCompanies(): Promise<Company[]> {
	await sleep(200);
	return COMPANIES;
}

export async function getRegistered(): Promise<RegisteredRow[]> {
	await sleep(300);
	return readRegistered();
}

export async function registerCompany(payload: RegisterPayload): Promise<string> {
	await sleep(250);
	validate(payload);

	const first = ++requests === 1;
	const branches = payload.commercial_register;
	for (const [i, branch] of branches.entries()) {
		const refuseCsid = first && scenario === "otp" && i === 0;
		const rejectInvoice = first && scenario === "reject" && i === branches.length - 1;
		await onboard(branch, refuseCsid, rejectInvoice);
		if (devices.get(branch.commercial_register_number)?.pcsid) saveRegistered(payload, branch);
	}
	return "Company Data Successfuly Saved";
}

async function onboard(branch: CommercialRegister, refuseCsid: boolean, rejectInvoice: boolean) {
	const crn = branch.commercial_register_number;
	const device = devices.get(crn) ?? { csid: false, tests: Array(6).fill(false), pcsid: false };
	devices.set(crn, device);
	const publish = (event: ZatcaEvent) =>
		listeners.forEach((l) => l({ commercial_register_name: crn, ...event }));

	if (!device.csid) {
		await sleep(1400);
		if (refuseCsid) {
			publish({ message: "Failed during CSID creation: Invalid OTP", indicator: "red", percentage: 0, complete: false });
			publish({ message: "ZATCA Setup Failed: Invalid OTP", indicator: "red", percentage: 0, complete: true });
			return;
		}
		device.csid = true;
		publish({ message: "CSID Created Successfully", indicator: "green", percentage: 20, complete: false });
		// saving_data_to_company's event carries no register, and the board must ignore it
		listeners.forEach((l) => l({ message: "Data Saved Successfully", indicator: "green" }));
	}

	let percentage = 20;
	for (const [i, [status, sub]] of SAMPLE_INVOICES.entries()) {
		if (device.tests[i]) continue;
		await sleep(800);
		if (rejectInvoice && i === 3) {
			publish({ message: `Invoice ${status}  Type ${sub} Was Rejected in Zatca`, indicator: "red", percentage });
			continue;
		}
		device.tests[i] = true;
		percentage += 10;
		publish({ message: `Invoice ${status}  Type ${sub} Was Accepted in Zatca`, indicator: "green", percentage });
	}

	if (device.tests.every(Boolean) && !device.pcsid) {
		await sleep(1200);
		device.pcsid = true;
		publish({ message: "Production CSID Created Successfully", indicator: "green", percentage: 95, complete: false });
	}

	publish(
		device.pcsid
			? { message: "ZATCA Setup Completed", indicator: "green", complete: true, percentage: 100 }
			: { message: "ZATCA Setup Partially Completed", indicator: "red", complete: true, percentage: 50 },
	);
}

function validate(payload: RegisterPayload) {
	for (const field of ["company", "company_name_in_arabic", "tax_id"] as const) {
		if (!payload[field]) throw serverError(`Missing Field ${field}`);
	}
	if (!TAX_ID.test(payload.tax_id)) {
		throw serverError("Tax ID must be 15 digits, starting and ending with 3");
	}
}

/** The shape frappe-ui's call() rejects with. */
function serverError(message: string) {
	return Object.assign(new Error(message), { exc_type: "ValidationError", messages: [message] });
}

function readRegistered(): RegisteredRow[] {
	return JSON.parse(localStorage.getItem(REGISTERED_KEY) ?? "[]");
}

function saveRegistered(payload: RegisterPayload, branch: CommercialRegister) {
	const rows = readRegistered().filter((r) => r.commercial_register_number !== branch.commercial_register_number);
	rows.push({
		...branch,
		company: payload.company,
		company_name_in_arabic: payload.company_name_in_arabic,
		tax_id: payload.tax_id,
		phase: payload.phase,
	});
	// v15 keeps one phase in Zatca Main Settings, so every row reports the latest.
	localStorage.setItem(REGISTERED_KEY, JSON.stringify(rows.map((r) => ({ ...r, phase: payload.phase }))));
}

function seedRow(name: string, crn: string, city: string, district: string): RegisteredRow {
	return {
		company: COMPANIES[0].name,
		company_name_in_arabic: COMPANIES[0].company_name_in_arabic!,
		tax_id: COMPANIES[0].tax_id!,
		commercial_register_name: name,
		commercial_register_number: crn,
		short_address: "RRRD2929",
		building_no: "2929",
		address_line1: "King Fahd Road",
		address_line2: "1234",
		city,
		district,
		pincode: "12211",
		otp: "",
		phase: "Phase Two",
	};
}

function sleep(ms: number) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
