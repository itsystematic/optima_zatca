import { describe, expect, it } from "vitest";
import { SUPPORT_WHATSAPP, deskUrl, supportWhatsApp } from "./desk";

describe("desk links", () => {
	it("addresses a doctype list", () => {
		expect(deskUrl("Sales Invoice")).toBe("/app/sales-invoice");
	});

	it("addresses a specific document", () => {
		expect(deskUrl("Sales Invoice", "new")).toBe("/app/sales-invoice/new");
		expect(deskUrl("E-Invoice Submission", "abc123")).toBe("/app/e-invoice-submission/abc123");
	});

	it("escapes a name that would otherwise break the path", () => {
		expect(deskUrl("Company", "My Company (Demo)")).toBe(
			"/app/company/My%20Company%20(Demo)",
		);
	});

	it("is absolute, so the router's basename cannot prefix it", () => {
		// navigate("/app/…") would resolve to /zatca-onboarding/app/…, which is nothing
		expect(deskUrl("Sales Invoice").startsWith("/app/")).toBe(true);
	});
});

describe("support message", () => {
	it("opens a chat with the support number", () => {
		expect(supportWhatsApp()).toContain(`https://wa.me/${SUPPORT_WHATSAPP}`);
	});

	it("carries no plus or spaces, which wa.me will not resolve", () => {
		expect(SUPPORT_WHATSAPP).toMatch(/^\d+$/);
	});

	it("leads with the reference, since that is what gets asked for first", () => {
		const url = supportWhatsApp({ reference: "SETUP-C00F" });
		expect(decodeURIComponent(url)).toContain("E-invoicing support — SETUP-C00F");
	});

	it("pre-fills the details the operator can see but WhatsApp cannot", () => {
		const body = decodeURIComponent(supportWhatsApp({ reference: "SETUP-1", company: "Acme" }));
		expect(body).toContain("Company: Acme");
		expect(body).toContain("Reference: SETUP-1");
	});

	it("omits what it does not have rather than writing a blank line", () => {
		const body = decodeURIComponent(supportWhatsApp());
		expect(body).not.toContain("Reference:");
		expect(body).not.toContain("Company:");
	});

	it("escapes the query, so a company name with an ampersand survives", () => {
		const url = supportWhatsApp({ company: "Smith & Sons" });
		expect(url).not.toContain("Smith & Sons");
		expect(decodeURIComponent(url)).toContain("Smith & Sons");
	});
});
