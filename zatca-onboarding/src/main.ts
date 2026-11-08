import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./style.css";

import { createApp } from "vue";
import App from "@/App.vue";
import { boot } from "@/boot";
import router from "@/router";
import { __ } from "@/translate";

async function start() {
	if (import.meta.env.DEV) {
		const { applyDevLanguage } = await import("@/devBoot");
		await applyDevLanguage(boot);
	}

	// frappe-ui's request helper reads the token from here.
	window.csrf_token = boot.csrf_token;
	document.documentElement.lang = boot.lang;
	document.documentElement.dir = boot.rtl ? "rtl" : "ltr";

	const app = createApp(App);
	app.config.globalProperties.__ = __;
	app.use(router);
	app.mount("#app");
}

start();

declare global {
	interface Window {
		csrf_token?: string;
	}
}

declare module "vue" {
	interface ComponentCustomProperties {
		__: typeof __;
	}
}
