import { call } from "frappe-ui";
import type { Company, RegisterPayload, RegisteredRow } from "@/types";

export { subscribeZatca } from "@/realtime";

export function getCompanies(): Promise<Company[]> {
	return call("frappe.client.get_list", {
		doctype: "Company",
		fields: ["name", "company_name_in_arabic", "tax_id"],
		order_by: "name asc",
		limit_page_length: 0,
	});
}

export function getRegistered(): Promise<RegisteredRow[]> {
	return call("optima_zatca.zatca.api.get_companies_registered");
}

/**
 * Resolves only once every register has been onboarded, because v15 does the
 * whole run inside this request. The board follows the realtime events instead
 * of waiting for it.
 */
export function registerCompany(payload: RegisterPayload): Promise<unknown> {
	return call("optima_zatca.zatca.api.register_company", {
		...payload,
		// validate_register_data only parses a JSON string; a list would reach it unparsed.
		commercial_register: JSON.stringify(payload.commercial_register),
	});
}
