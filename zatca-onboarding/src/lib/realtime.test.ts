import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * The socket is the enhancement; polling is the guarantee. These check the part
 * that decides between them, because a board that silently stops updating is worse
 * than one that updates coarsely.
 */

const connections: { url: string }[] = [];

vi.mock("socket.io-client", () => ({
	io: (url: string) => {
		connections.push({ url });
		return {
			connected: false,
			on: () => {},
			off: () => {},
			close: () => {},
			io: { on: () => {}, reconnectionAttempts: () => 3 },
		};
	},
}));

async function load() {
	vi.resetModules();
	connections.length = 0;
	return import("./realtime");
}

afterEach(() => {
	delete (window as unknown as { optima_socketio_port?: string }).optima_socketio_port;
});

describe("choosing where the socket lives", () => {
	it("tries this origin first, which is where a proxy puts it", async () => {
		const rt = await load();
		rt.subscribe("optima_zatca_run_progress", () => {});
		expect(connections[0].url).toBe(window.location.origin);
		rt.reset();
	});

	it("reports not connected until a socket actually connects", async () => {
		const rt = await load();
		rt.subscribe("optima_zatca_run_progress", () => {});
		// the mock never fires `connect`, which is the case that must fall back
		expect(rt.isConnected()).toBe(false);
		rt.reset();
	});

	it("ignores an unrendered template placeholder as a port", async () => {
		(window as unknown as { optima_socketio_port?: string }).optima_socketio_port =
			"{{ socketio_port }}";
		const rt = await load();
		rt.subscribe("optima_zatca_run_progress", () => {});
		// one candidate only: the origin. A placeholder is not a port number.
		expect(connections).toHaveLength(1);
		rt.reset();
	});

	it("connects once for several subscriptions", async () => {
		const rt = await load();
		rt.subscribe("optima_zatca_run_progress", () => {});
		rt.subscribe("optima_zatca_invoice_settled", () => {});
		expect(connections).toHaveLength(1);
		rt.reset();
	});
});

describe("unsubscribing", () => {
	it("hands back a function that removes the listener", async () => {
		const rt = await load();
		const stop = rt.subscribe("optima_zatca_run_progress", () => {});
		expect(typeof stop).toBe("function");
		stop();
		rt.reset();
	});

	it("survives being called with no socket available", async () => {
		const rt = await load();
		const stop = rt.subscribe("optima_zatca_run_progress", () => {});
		rt.reset();
		expect(() => stop()).not.toThrow();
	});
});
