import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Fragment, createElement } from "react";
import type { Message, Params } from "./types";
import { en } from "./en";
import { ar } from "./ar";

export type Lang = "en" | "ar";
export type MessageKey = keyof typeof en;

const DICTIONARIES: Record<Lang, Record<MessageKey, Message>> = { en, ar };

export const LANGUAGES: { code: Lang; label: string; native: string }[] = [
	{ code: "en", label: "English", native: "EN" },
	{ code: "ar", label: "Arabic", native: "ع" },
];

const RTL_LANGS: Lang[] = ["ar"];

type I18n = {
	lang: Lang;
	setLang: (lang: Lang) => void;
	dir: "ltr" | "rtl";
	/** Plain string, for attributes, titles and anything not rendered as nodes. */
	t: (key: MessageKey, params?: Params) => string;
};

const I18nContext = createContext<I18n | null>(null);

/** `?lang=ar` deep-links a translated screen; otherwise start in English. */
function initialLang(): Lang {
	if (typeof window === "undefined") return "en";
	const search = new URLSearchParams(window.location.search);
	const requested = search.get("lang");
	if (requested === "ar" || requested === "en") return requested;
	// `?rtl=1` predates the translations and still means "show me the mirror"
	return search.get("rtl") === "1" ? "ar" : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
	const [lang, setLang] = useState<Lang>(initialLang);

	const t = useCallback(
		(key: MessageKey, params?: Params) => format(resolve(lang, key, params), params),
		[lang],
	);

	const dir = RTL_LANGS.includes(lang) ? "rtl" : "ltr";

	// the document element carries the language so the stylesheet can swap the
	// interface face, and so assistive technology announces the right one
	useEffect(() => {
		document.documentElement.lang = lang;
		document.documentElement.dir = dir;
	}, [lang, dir]);

	const value = useMemo<I18n>(() => ({ lang, setLang, dir, t }), [lang, dir, t]);

	return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
	const ctx = useContext(I18nContext);
	if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
	return ctx;
}

/** Shorthand for the common case. */
export function useT() {
	return useI18n().t;
}

/**
 * Pick the right string for a key, choosing a plural form when the message
 * declares them. A language that does not translate a key falls back to English
 * rather than showing the key itself.
 */
function resolve(lang: Lang, key: MessageKey, params?: Params): string {
	const message = DICTIONARIES[lang][key] ?? en[key];
	// an unknown key renders as itself, which is what lets a caller detect a miss
	// and fall back to text the server supplied
	if (message === undefined) return String(key);
	if (typeof message === "string") return message;

	const count = Number(params?.count ?? 0);
	const rule = new Intl.PluralRules(lang).select(count);
	return message[rule] ?? message.other ?? Object.values(message)[0] ?? String(key);
}

/** Replace `{name}` placeholders, localising any numbers on the way through. */
function format(template: string, params?: Params): string {
	if (!params) return template;
	return template.replace(/\{(\w+)\}/g, (whole, name: string) => {
		const value = params[name];
		return value === undefined ? whole : String(value);
	});
}

/**
 * Render a message as nodes, so translators can move emphasis around inside a
 * sentence instead of the layout hard-coding where the bold half sits.
 *
 *   *emphasis*  → <b>
 *   `literal`   → monospace, for field values and menu paths
 */
export function T({ k, params }: { k: MessageKey; params?: Params }) {
	const { lang } = useI18n();
	const text = format(resolve(lang, k, params), params);
	return createElement(Fragment, null, ...parse(text));
}

/** The same markup rules, for places that need nodes without the component. */
export function rich(text: string): ReactNode[] {
	return parse(text);
}

function parse(text: string): ReactNode[] {
	const nodes: ReactNode[] = [];
	const pattern = /\*([^*]+)\*|`([^`]+)`/g;
	let last = 0;
	let match: RegExpExecArray | null;
	let key = 0;

	while ((match = pattern.exec(text)) !== null) {
		if (match.index > last) nodes.push(text.slice(last, match.index));
		if (match[1] !== undefined) {
			nodes.push(createElement("b", { key: key++ }, match[1]));
		} else {
			nodes.push(
				createElement("span", { key: key++, className: "mono", style: { fontSize: "0.94em" } }, match[2]),
			);
		}
		last = pattern.lastIndex;
	}
	if (last < text.length) nodes.push(text.slice(last));
	return nodes;
}
