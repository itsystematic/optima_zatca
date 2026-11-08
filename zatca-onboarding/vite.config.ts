import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import fs from "node:fs";
import type { ServerResponse } from "node:http";
import path from "node:path";
import { defineConfig, type Connect, type Plugin, type ProxyOptions } from "vite";

const src = path.resolve(__dirname, "src");
const useMock = process.env.VITE_ZATCA_API === "mock";

export default defineConfig({
	plugins: [
		// Proxy, boot data and build output are configured below, the way the
		// other bench SPAs do it; the plugin is kept for its dependency handling.
		frappeui({ frappeProxy: false, jinjaBootData: false, buildConfig: false }),
		vue(),
		devFiles(),
	],
	server: {
		port: 8200,
		proxy: useMock ? undefined : proxyOptions(),
		allowedHosts: true,
	},
	resolve: {
		alias: {
			"@": src,
			// The mock is swapped in here rather than behind a runtime flag, so a
			// production build cannot contain it.
			"#backend": path.join(src, "api", useMock ? "mock.ts" : "live.ts"),
		},
	},
	build: {
		outDir: "../optima_zatca/public/zatca-onboarding",
		emptyOutDir: true,
		target: "es2020",
	},
});

/**
 * Files the dev server hands out from the app itself: the translation CSVs that
 * devBoot.ts reads for `?lang=`, and, with no Frappe behind the mock, the app's
 * public files at the path Frappe would serve them.
 */
function devFiles(): Plugin {
	const app = path.resolve(__dirname, "../optima_zatca");
	const TYPES: Record<string, string> = {
		".csv": "text/csv; charset=utf-8",
		".ttf": "font/ttf",
		".webp": "image/webp",
		".png": "image/png",
	};
	const serve = (root: string) => (req: Connect.IncomingMessage, res: ServerResponse, next: () => void) => {
		const file = path.join(root, decodeURIComponent((req.url ?? "").split("?")[0]));
		if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
			return next();
		}
		res.setHeader("Content-Type", TYPES[path.extname(file)] ?? "application/octet-stream");
		fs.createReadStream(file).pipe(res);
	};
	return {
		name: "optima-zatca-dev-files",
		apply: "serve",
		configureServer(server) {
			server.middlewares.use("/__dev/translations", serve(path.join(app, "translations")));
			if (useMock) server.middlewares.use("/assets/optima_zatca", serve(path.join(app, "public")));
		},
	};
}

function proxyOptions(): Record<string, ProxyOptions> {
	const config = commonSiteConfig();
	const webserver = config.webserver_port ?? 8000;
	const socketio = config.socketio_port ?? 9000;
	// The browser's host is the site name, exactly as when Frappe serves the page.
	const site = (req: { headers: { host?: string } }) => (req.headers.host ?? "").split(":")[0];

	return {
		"^/(app|desk|login|api|assets|files|private)": {
			target: `http://127.0.0.1:${webserver}`,
			router: (req) => `http://${site(req)}:${webserver}`,
		},
		"/socket.io": {
			target: `http://127.0.0.1:${socketio}`,
			ws: true,
			router: (req) => `http://${site(req)}:${socketio}`,
		},
	};
}

function commonSiteConfig(): { webserver_port?: number; socketio_port?: number } {
	let dir = __dirname;
	while (dir !== path.dirname(dir)) {
		const file = path.join(dir, "sites", "common_site_config.json");
		if (fs.existsSync(file)) return JSON.parse(fs.readFileSync(file, "utf8"));
		dir = path.dirname(dir);
	}
	return {};
}
