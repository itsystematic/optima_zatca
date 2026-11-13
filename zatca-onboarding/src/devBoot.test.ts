import { describe, expect, it } from "vitest";
import { parsePo } from "./devBoot";

const PO = `msgid ""
msgstr ""
"Language: ar\\n"

msgctxt "onboarding"
msgid "Back"
msgstr "رجوع"

#. a comment
msgid "Back"
msgstr "السابق"

msgid ""
"Line one\\n"
"line \\"two\\""
msgstr "سطر\\n\\"اثنان\\""

msgid "Untranslated"
msgstr ""
`;

describe("parsePo", () => {
	const out = parsePo(PO);

	it("keys a context entry as msgid:msgctxt, the way Frappe does", () => {
		expect(out["Back:onboarding"]).toBe("رجوع");
		expect(out["Back"]).toBe("السابق");
	});

	it("joins continuation lines and unescapes quotes and newlines", () => {
		expect(out['Line one\nline "two"']).toBe('سطر\n"اثنان"');
	});

	it("skips the header and untranslated entries", () => {
		expect(out[""]).toBeUndefined();
		expect("Untranslated" in out).toBe(false);
	});
});
