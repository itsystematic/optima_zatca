import { boot } from "@/boot";

/**
 * Frappe's `__()`: look the source string up (under `source:context` first, as
 * Frappe stores a CSV row's third column), then fill `{0}`, `{1}`…
 */
export function __(message: string, replace?: (string | number)[], context?: string): string {
	let text = (context && boot.translations[`${message}:${context}`]) || boot.translations[message] || message;
	replace?.forEach((value, i) => {
		text = text.split(`{${i}}`).join(String(value));
	});
	return text;
}
