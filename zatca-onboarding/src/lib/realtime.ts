import { io, type Socket } from "socket.io-client";

/**
 * Frappe's socket.io connection, for the one screen that needs to be told rather
 * than to keep asking.
 *
 * The progress board polled every 900ms. That is a poor way to animate a five
 * stage run: an update lands somewhere inside the window, so a stage that took
 * 200ms is either missed or arrives late, and the bar moves in visible steps
 * instead of following the work.
 *
 * Polling is kept as the fallback, not removed. A socket is the thing most likely
 * to be missing — `bench start` serves it on another port, a reverse proxy may not
 * forward it, and the mock backend has no server at all — and a board that stops
 * updating is worse than one that updates coarsely.
 */

/** Where the page says the socket lives; absent in the dev server and the mock. */
function configuredPort(): string | null {
	const raw = (window as unknown as { optima_socketio_port?: string }).optima_socketio_port;
	// an unrendered Jinja placeholder is not a port
	return raw && /^\d+$/.test(raw) ? raw : null;
}

/**
 * Candidate URLs, in the order they are worth trying.
 *
 * Same origin first: that is where a reverse proxy puts it in production, and it
 * carries the session cookie without further thought. The explicit port is the
 * development shape, where the app is served on one port and socket.io on another.
 */
function candidates(): string[] {
	const urls = [window.location.origin];
	const port = configuredPort();
	if (port && port !== window.location.port) {
		urls.push(`${window.location.protocol}//${window.location.hostname}:${port}`);
	}
	return urls;
}

type Listener = (payload: unknown) => void;

let socket: Socket | null = null;
let attempt = 0;
const listeners = new Map<string, Set<Listener>>();
const statusWatchers = new Set<(connected: boolean) => void>();

function announce(connected: boolean) {
	for (const watcher of statusWatchers) watcher(connected);
}

/** Whether a live connection is up, which is what decides if polling is needed. */
export function isConnected(): boolean {
	return socket?.connected ?? false;
}

export function watchConnection(watcher: (connected: boolean) => void): () => void {
	statusWatchers.add(watcher);
	return () => statusWatchers.delete(watcher);
}

function connect(): Socket | null {
	const urls = candidates();
	if (attempt >= urls.length) return null;

	const url = urls[attempt];
	const next = io(url, {
		path: "/socket.io",
		withCredentials: true,
		// the fallback exists, so give up quickly rather than leaving the board
		// waiting on a socket that is not coming
		reconnectionAttempts: 3,
		timeout: 4000,
		transports: ["websocket", "polling"],
	});

	next.on("connect", () => announce(true));
	next.on("disconnect", () => announce(false));
	next.on("connect_error", () => {
		announce(false);
		// try the next candidate once this one is exhausted, then stop and let the
		// caller poll
		if (next.io.reconnectionAttempts() === 0) return;
	});
	next.io.on("reconnect_failed", () => {
		next.close();
		socket = null;
		attempt += 1;
		announce(false);
		connect();
	});

	// re-attach whatever was already subscribed, so a caller does not have to know
	// which connection attempt it landed on
	for (const [event, handlers] of listeners) {
		for (const handler of handlers) next.on(event, handler);
	}

	socket = next;
	return next;
}

/**
 * Listen for one of Frappe's realtime events.
 *
 * Safe to call when no socket is available: the subscription is remembered and
 * attached if one comes up, and the caller's fallback keeps working meanwhile.
 */
export function subscribe(event: string, handler: Listener): () => void {
	let handlers = listeners.get(event);
	if (!handlers) {
		handlers = new Set();
		listeners.set(event, handlers);
	}
	handlers.add(handler);

	const live = socket ?? connect();
	live?.on(event, handler);

	return () => {
		handlers?.delete(handler);
		socket?.off(event, handler);
		if (handlers && handlers.size === 0) listeners.delete(event);
	};
}

/** Drop the connection. Only the tests need this; a page keeps it for its lifetime. */
export function reset(): void {
	socket?.close();
	socket = null;
	attempt = 0;
	listeners.clear();
	statusWatchers.clear();
}
