import type { Boot } from "@/boot";

const RTL = ["ar", "fa", "he", "ps", "ur"];

/**
 * Under the Vite dev server no Frappe page renders the boot data, so `?lang=ar`
 * stands in for the user's language and the app's own CSV (served by the dev
 * server, see vite.config.ts) for its translations.
 */
export async function applyDevLanguage(boot: Boot) {
	const lang = new URLSearchParams(window.location.search).get("lang");
	if (!lang || lang === "en") return;
	const response = await fetch(`/__dev/translations/${encodeURIComponent(lang)}.csv`);
	if (!response.ok) return;
	boot.lang = lang;
	boot.rtl = RTL.includes(lang);
	boot.translations = parseTranslations(await response.text());
}

/** Rows are `source,translation[,context]`, keyed the way Frappe keys them. */
function parseTranslations(csv: string): Record<string, string> {
	const out: Record<string, string> = {};
	for (const [source, target, context] of parseCsv(csv)) {
		if (source && target) out[context ? `${source}:${context}` : source] = target;
	}
	return out;
}

function parseCsv(text: string): string[][] {
	const rows: string[][] = [];
	let row: string[] = [];
	let field = "";
	let quoted = false;
	for (let i = 0; i < text.length; i++) {
		const c = text[i];
		if (quoted) {
			if (c === '"' && text[i + 1] === '"') {
				field += '"';
				i++;
			} else if (c === '"') quoted = false;
			else field += c;
		} else if (c === '"') quoted = true;
		else if (c === ",") {
			row.push(field);
			field = "";
		} else if (c === "\n" || c === "\r") {
			if (c === "\r" && text[i + 1] === "\n") i++;
			row.push(field);
			rows.push(row);
			row = [];
			field = "";
		} else field += c;
	}
	if (field || row.length) rows.push([...row, field]);
	return rows;
}
