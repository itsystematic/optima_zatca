import preset, { content } from "frappe-ui/tailwind";

/** @type {import('tailwindcss').Config} */
export default {
	presets: [preset],
	content: [...content, "./index.html", "./src/**/*.{vue,ts}"],
	theme: {
		extend: {
			// The IT Systematic palette, sampled from the logo's navy-to-magenta sweep.
			colors: {
				brand: {
					DEFAULT: "#73006c",
					hover: "#520059",
					tint: "#f3e8f1",
					"tint-2": "#fbf6fa",
					line: "#dcc0d7",
					"line-2": "#ebdce8",
					"line-3": "#be93b7",
				},
				navy: "#01002b",
				canvas: "#dedce4",
				desk: "#f4f3f6",
				ok: { DEFAULT: "#1f7a44", tint: "#e8f3ec" },
				warn: { DEFAULT: "#a6690c", band: "#edd9ae" },
				danger: { DEFAULT: "#b3261e", tint: "#fdf6f5" },
				hair: "#eeedf2",
				line: "#c8c5d1",
			},
			fontFamily: {
				sans: ['"IBM Plex Sans"', "Almarai", "system-ui", "sans-serif"],
				mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
			},
		},
	},
};
