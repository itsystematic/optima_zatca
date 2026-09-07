/** Presentation helpers shared across the flow. */

export function mmss(totalSeconds: number): string {
	const s = Math.max(0, Math.round(totalSeconds));
	return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

const DATE = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const DATE_TIME = new Intl.DateTimeFormat("en-GB", {
	day: "numeric",
	month: "short",
	year: "numeric",
	hour: "2-digit",
	minute: "2-digit",
	hour12: false,
});

export const formatDate = (iso: string) => DATE.format(new Date(iso));
export const formatDateTime = (iso: string) => DATE_TIME.format(new Date(iso)).replace(",", ",");

/** "12 seconds ago" for the autosave line in the desk bar. */
export function relativeTime(iso: string, now = Date.now()): string {
	const seconds = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
	if (seconds < 5) return "just now";
	if (seconds < 60) return `${seconds} seconds ago`;
	const minutes = Math.round(seconds / 60);
	if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
	return formatDate(iso);
}

export function pluralise(n: number, one: string, many = `${one}s`): string {
	return `${n} ${n === 1 ? one : many}`;
}

/** The address as it reads in the review table. */
export function oneLineAddress(a: {
	buildingNumber: string;
	street: string;
	district: string;
	postalCode: string;
}): string {
	return [a.buildingNumber, a.street].filter(Boolean).join(" ") +
		[a.district, a.postalCode].filter(Boolean).map((p) => `, ${p}`).join("");
}

const SPELLED = [
	"zero",
	"one",
	"two",
	"three",
	"four",
	"five",
	"six",
	"seven",
	"eight",
	"nine",
	"ten",
];

/** Prose reads better with small numbers spelled out; tables and stats do not. */
export function spell(n: number): string {
	return SPELLED[n] ?? String(n);
}
