import { describe, expect, it } from "vitest";
import { en } from "./en";
import { ar } from "./ar";
import type { Message } from "./types";

/**
 * The catalogues are checked structurally: a key that exists in one language and
 * not the other, or a plural that forgets a form Arabic actually uses, is a bug
 * you would otherwise only find on the screen it breaks.
 */

const KEYS = Object.keys(en) as (keyof typeof en)[];

/** Placeholders a message expects, e.g. `{count}`. */
const placeholders = (message: Message): Set<string> => {
	const found = new Set<string>();
	const texts = typeof message === "string" ? [message] : Object.values(message);
	for (const text of texts) {
		for (const match of text.matchAll(/\{(\w+)\}/g)) found.add(match[1]);
	}
	return found;
};

describe("catalogues", () => {
	it("cover the same keys", () => {
		expect(Object.keys(ar).sort()).toEqual(KEYS.slice().sort());
	});

	it("never leave a message empty", () => {
		for (const key of KEYS) {
			const texts =
				typeof ar[key] === "string" ? [ar[key] as string] : Object.values(ar[key] as object);
			for (const text of texts) expect(text, key).not.toBe("");
		}
	});

	it("declare every plural form Arabic selects for a plausible count", () => {
		const rules = new Intl.PluralRules("ar");
		const counts = [0, 1, 2, 3, 5, 10, 11, 25, 99, 100];

		for (const key of KEYS) {
			const message = ar[key];
			if (typeof message === "string") continue;
			for (const count of counts) {
				const form = rules.select(count);
				const usable = message[form] ?? message.other;
				expect(usable, `${key} has no form for ${form} (count ${count})`).toBeTruthy();
			}
		}
	});

	it("keep the same placeholders in both languages", () => {
		for (const key of KEYS) {
			const source = placeholders(en[key]);
			const target = placeholders(ar[key]);
			for (const name of target) {
				expect(source.has(name), `${key} interpolates {${name}} in Arabic but not in English`).toBe(
					true,
				);
			}
		}
	});

	it("balance the emphasis and literal markers", () => {
		for (const key of KEYS) {
			for (const message of [en[key], ar[key]]) {
				const texts = typeof message === "string" ? [message] : Object.values(message);
				for (const text of texts) {
					expect((text.match(/\*/g) ?? []).length % 2, `${key}: unbalanced *`).toBe(0);
					expect((text.match(/`/g) ?? []).length % 2, `${key}: unbalanced backtick`).toBe(0);
				}
			}
		}
	});
});
