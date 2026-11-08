import { io, type Socket } from "socket.io-client";
import { boot } from "@/boot";
import type { ZatcaEvent } from "@/types";

let socket: Socket | null = null;

/**
 * The URL Frappe's own desk client builds (socketio_client.js get_host): the
 * site name is the namespace, and the server refuses a connection without it.
 */
function socketUrl(): string {
	const { protocol, hostname, origin } = window.location;
	const base = boot.socketio_port ? `${protocol}//${hostname}:${boot.socketio_port}` : origin;
	return `${base}/${boot.site_name}`;
}

export function subscribeZatca(handler: (event: ZatcaEvent) => void): () => void {
	socket ??= io(socketUrl(), { withCredentials: true, reconnectionAttempts: 3 });
	socket.on("zatca", handler);
	return () => {
		socket?.off("zatca", handler);
	};
}
