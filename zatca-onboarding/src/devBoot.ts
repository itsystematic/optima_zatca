import type { Boot } from "@/boot";

const RTL = ["ar", "fa", "he", "ps", "ur"];

/**
 * Under the Vite dev server no Frappe page renders the boot data, so `?lang=ar`
 * stands in for the user's language and the app's own PO catalog (locale/<lang>.po,
 * served by the dev server, see vite.config.ts) for its translations.
 */
export async function applyDevLanguage(boot: Boot) {
	const lang = new URLSearchParams(window.location.search).get("lang");
	if (!lang || lang === "en") return;
	const response = await fetch(`/__dev/locale/${encodeURIComponent(lang)}.po`);
	if (!response.ok) return;
	boot.lang = lang;
	boot.rtl = RTL.includes(lang);
	boot.translations = parsePo(await response.text());
}

/** Entries keyed the way Frappe keys them: `msgid`, or `msgid:msgctxt` with a context. */
export function parsePo(text: string): Record<string, string> {
	const out: Record<string, string> = {};
	let entry: Record<string, string> = {};
	let field = "";
	const flush = () => {
		const { msgid, msgstr, msgctxt } = entry;
		if (msgid && msgstr) out[msgctxt ? `${msgid}:${msgctxt}` : msgid] = msgstr;
		entry = {};
		field = "";
	};
	for (const raw of text.split(/\r?\n/)) {
		const line = raw.trim();
		if (!line) {
			flush();
			continue;
		}
		if (line.startsWith("#")) continue;
		const keyword = line.match(/^(msgctxt|msgid|msgstr)(?:\[0\])?\s+(".*")$/);
		if (keyword) {
			if (keyword[1] === "msgctxt" || (keyword[1] === "msgid" && "msgstr" in entry)) flush();
			field = keyword[1];
			entry[field] = unquote(keyword[2]);
		} else if (line.startsWith('"') && field) {
			entry[field] += unquote(line);
		} else {
			field = ""; // msgid_plural or a later plural form: not used by the wizard
		}
	}
	flush();
	return out;
}

function unquote(quoted: string): string {
	return quoted
		.slice(1, -1)
		.replace(/\\(.)/g, (_, c: string) => ({ n: "\n", t: "\t", r: "\r" })[c] ?? c);
}
