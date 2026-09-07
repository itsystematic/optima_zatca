import { describe, expect, it } from "vitest";
import { GLOBAL_KEYS, SCOPED_KEYS, SETUP_DERIVED_KEYS, qk } from "./keys";

/** The first segment is what `removeQueries` matches a key by. */
const prefix = (key: readonly unknown[]) => String(key[0]);

describe("company-scoped cache keys", () => {
	it("classifies every read as scoped or global", () => {
		const declared = new Set([...SCOPED_KEYS, ...GLOBAL_KEYS].map(prefix));
		const reads = Object.values(qk).map((entry) =>
			prefix(typeof entry === "function" ? entry("R") : entry),
		);
		for (const read of reads) {
			// a new query has to be decided about: dropped on a company switch, or
			// deliberately kept. Neither is the default.
			expect(declared, `${read} is neither scoped nor global`).toContain(read);
		}
	});

	it("keeps the two sets disjoint", () => {
		const scoped = SCOPED_KEYS.map(prefix);
		for (const global of GLOBAL_KEYS.map(prefix)) {
			expect(scoped).not.toContain(global);
		}
	});

	it("drops the setup record, which is the whole point", () => {
		expect(SCOPED_KEYS.map(prefix)).toContain(prefix(qk.setup));
	});

	it("keeps the company list, which is what the picker is reading", () => {
		expect(GLOBAL_KEYS.map(prefix)).toContain(prefix(qk.companies));
	});

	it("drops a register log, which names a register of the company being left", () => {
		expect(SCOPED_KEYS.map(prefix)).toContain(prefix(qk.registerLog("R1")));
	});
});

describe("reads that go stale when a setup moves", () => {
	/**
	 * Being global is about which company is chosen; being setup-derived is about
	 * how far along that company's setup is. The company list is both, and treating
	 * the first as covering the second is what left a registered company showing as
	 * unregistered.
	 */
	it("counts the company list, because it reports each setup's status", () => {
		expect(SETUP_DERIVED_KEYS.map(prefix)).toContain(prefix(qk.companies));
	});

	it("is not an excuse to skip removing the scoped ones", () => {
		const derived = SETUP_DERIVED_KEYS.map(prefix);
		for (const scoped of SCOPED_KEYS.map(prefix)) {
			expect(derived, `${scoped} is scoped, so it must be removed, not invalidated`)
				.not.toContain(scoped);
		}
	});

	it("holds nothing that is not also a declared read", () => {
		const known = Object.values(qk).map((entry) =>
			prefix(typeof entry === "function" ? entry("R") : entry),
		);
		for (const key of SETUP_DERIVED_KEYS.map(prefix)) expect(known).toContain(key);
	});
});
