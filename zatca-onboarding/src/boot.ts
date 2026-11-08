export interface Boot {
	csrf_token: string;
	site_name: string;
	/** Set only under `bench start`, where socket.io listens on its own port. */
	socketio_port: string | number | null;
	lang: string;
	rtl: boolean;
	translations: Record<string, string>;
}

function read(): Boot {
	const fallback: Boot = {
		csrf_token: "",
		site_name: window.location.hostname,
		socketio_port: null,
		lang: "en",
		rtl: false,
		translations: {},
	};
	try {
		const text = document.getElementById("zatca-boot")?.textContent ?? "";
		return { ...fallback, ...JSON.parse(text) };
	} catch {
		return fallback;
	}
}

export const boot = read();
