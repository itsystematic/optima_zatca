import { beforeEach, describe, expect, it } from "vitest";
import { scopedCompany, setCompanyScope } from "./scope";

/**
 * The company scope decides which setup every call reads and writes. Getting it
 * wrong is not a display bug — it silently edits another company's registration.
 */

const withSearch = (search: string) => {
	window.history.replaceState({}, "", `/setup${search}`);
};

beforeEach(() => {
	sessionStorage.clear();
	withSearch("");
});

describe("company scope", () => {
	it("defers to the server when nothing has been chosen", () => {
		expect(scopedCompany()).toBeUndefined();
	});

	it("takes the company named in the URL", () => {
		withSearch("?company=Acme%20Ltd");
		expect(scopedCompany()).toBe("Acme Ltd");
	});

	/**
	 * The router drops query parameters as it navigates, so a scope read from the
	 * current URL would silently revert to the default company on the next step.
	 */
	it("holds the choice after the parameter is gone", () => {
		withSearch("?company=Acme%20Ltd");
		expect(scopedCompany()).toBe("Acme Ltd");
		withSearch("/registers");
		expect(scopedCompany()).toBe("Acme Ltd");
	});

	it("is cleared by an empty parameter, handing control back to the server", () => {
		setCompanyScope("Acme Ltd");
		withSearch("?company=");
		expect(scopedCompany()).toBeUndefined();
	});

	it("can be moved to another company outright", () => {
		setCompanyScope("Acme Ltd");
		expect(scopedCompany()).toBe("Acme Ltd");
		setCompanyScope("Globex");
		expect(scopedCompany()).toBe("Globex");
		setCompanyScope(null);
		expect(scopedCompany()).toBeUndefined();
	});
});
