import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { IncomingMessage } from "node:http";
import type { ProxyOptions } from "vite";

/**
 * Point the dev server at the local bench.
 *
 * Frappe picks the site from the `Host` header, so the proxy target has to carry
 * the site's own name rather than `localhost`. Open the app at
 * `http://<site>:8300` and it routes itself; otherwise set `BENCH_SITE`, or let
 * it fall back to `currentsite.txt` or the only site on the bench.
 */

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITES = path.resolve(HERE, "../../../sites");

const read = (file: string): string | null => {
	try {
		return fs.readFileSync(path.join(SITES, file), "utf8");
	} catch {
		return null;
	}
};

function webserverPort(): number {
	const raw = read("common_site_config.json");
	if (!raw) return 8000;
	try {
		return Number(JSON.parse(raw).webserver_port) || 8000;
	} catch {
		return 8000;
	}
}

/** Directory names on the bench that are actually sites. */
function sites(): string[] {
	try {
		return fs
			.readdirSync(SITES, { withFileTypes: true })
			.filter(
				(entry) =>
					entry.isDirectory() && fs.existsSync(path.join(SITES, entry.name, "site_config.json")),
			)
			.map((entry) => entry.name);
	} catch {
		return [];
	}
}

function defaultSite(known: string[]): string | null {
	if (process.env.BENCH_SITE) return process.env.BENCH_SITE;
	const current = read("currentsite.txt")?.trim();
	if (current) return current;
	return known.length === 1 ? known[0] : null;
}

const PORT = webserverPort();
const KNOWN = sites();
const FALLBACK = defaultSite(KNOWN);

if (!FALLBACK && KNOWN.length > 1) {
	console.warn(
		`\n[optima-zatca] ${KNOWN.length} sites on this bench (${KNOWN.join(", ")}) and no default.\n` +
			`       Open the app at http://<site>:8300, or start it with BENCH_SITE=<site>.\n`,
	);
}

/** The site to address for one request: the browser's own host, if it is one. */
function siteFor(req: IncomingMessage): string {
	const host = (req.headers.host ?? "").split(":")[0];
	if (KNOWN.includes(host)) return host;
	return FALLBACK ?? host;
}

const bench: ProxyOptions = {
	target: `http://127.0.0.1:${PORT}`,
	ws: true,
	// Frappe resolves the site from the Host header, so it is rewritten per
	// request rather than left as the dev server's own address.
	changeOrigin: false,
	configure: (proxy) => {
		proxy.on("proxyReq", (proxyReq, req) => {
			proxyReq.setHeader("host", `${siteFor(req as IncomingMessage)}:${PORT}`);
		});
	},
};

export default {
	"^/(api|assets|files|private|app)": bench,
} satisfies Record<string, ProxyOptions>;
