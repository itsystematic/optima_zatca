<script setup lang="ts">
import flagUrl from "@/assets/saudi.webp";

withDefaults(defineProps<{ height?: number }>(), { height: 132 });

/** Seven fronds that rise from the crown and droop at the tip, which is what reads as a palm. */
const FRONDS = [
	"M1.5 0 C0.5 -14 -0.5 -28 -0.5 -42",
	"M-0.5 -42 C -8 -52 -20 -54 -28 -47",
	"M-0.5 -42 C 7 -52 19 -54 27 -47",
	"M-0.5 -42 C -6 -54 -14 -61 -21 -62",
	"M-0.5 -42 C 5 -54 13 -61 20 -62",
	"M-0.5 -42 C -3 -55 -7 -64 -11 -69",
	"M-0.5 -42 C 2 -55 6 -64 10 -69",
	"M-0.5 -42 C -0.5 -54 -0.5 -63 0.5 -70",
];
const PALMS = [
	{ x: 34, scale: 1 },
	{ x: 846, scale: 0.82 },
];
const BACK = [
	[60, 80, 34, 40],
	[100, 90, 26, 30],
	[132, 72, 30, 48],
	[262, 76, 26, 44],
	[294, 86, 34, 34],
	[336, 66, 24, 54],
	[500, 78, 30, 42],
	[536, 64, 22, 56],
	[700, 82, 32, 38],
	[738, 70, 24, 50],
	[856, 84, 30, 36],
	[892, 92, 24, 28],
];
// The flag is the supplied artwork at its official 2:3 proportion, never redrawn.
const FLAG = { x: 928, y: 38, width: 82, height: (82 * 2) / 3 };
</script>

<template>
	<svg
		viewBox="0 0 1040 132"
		width="100%"
		:height="height"
		preserveAspectRatio="xMidYMax slice"
		class="block"
		aria-hidden="true"
		focusable="false"
	>
		<g class="fill-brand-line-2">
			<rect v-for="([x, y, w, h], i) in BACK" :key="i" :x="x" :y="y" :width="w" :height="h" />
		</g>

		<g class="fill-brand-line" opacity="0.85">
			<!-- Al Faisaliah -->
			<path d="M190 120 L198.6 40 L201.4 40 L210 120 Z" />
			<circle cx="200" cy="47" r="8" />
			<rect x="199.2" y="12" width="1.6" height="28" />
			<!-- Kingdom Centre: one path with an enclosed hole, so the opening cannot reach the ground -->
			<path
				fill-rule="evenodd"
				d="M404 120 L456 120 L456 44 C456 18 404 18 404 44 Z M418 78 L442 78 L442 50 C442 34 418 34 418 50 Z"
			/>
			<rect x="416" y="46" width="28" height="4" />
			<!-- a mosque between two minarets -->
			<rect x="586" y="56" width="6" height="64" />
			<circle cx="589" cy="53" r="5" />
			<rect x="588.2" y="34" width="1.6" height="16" />
			<rect x="600" y="98" width="46" height="22" />
			<path d="M600 98 A23 23 0 0 1 646 98 Z" />
			<rect x="622.2" y="64" width="1.6" height="14" />
			<rect x="652" y="56" width="6" height="64" />
			<circle cx="655" cy="53" r="5" />
			<rect x="654.2" y="34" width="1.6" height="16" />
			<!-- a stepped tower and its mast -->
			<path d="M772 120 L772 60 L784 60 L784 44 L800 44 L800 60 L812 60 L812 120 Z" />
			<rect x="791.2" y="20" width="1.6" height="26" />
		</g>

		<g fill="none" class="stroke-brand-line" stroke-width="2.4" stroke-linecap="round" opacity="0.85">
			<g v-for="palm in PALMS" :key="palm.x" :transform="`translate(${palm.x} 120) scale(${palm.scale})`">
				<path v-for="d in FRONDS" :key="d" :d="d" />
			</g>
		</g>

		<g :transform="`translate(${FLAG.x} ${FLAG.y})`">
			<rect x="-5" y="-5" width="2.4" :height="132 - FLAG.y + 5" class="fill-brand-line-3" />
			<circle cx="-3.8" cy="-7" r="2.4" class="fill-brand-line-3" />
			<image :href="flagUrl" :width="FLAG.width" :height="FLAG.height" preserveAspectRatio="xMidYMid meet" />
		</g>

		<rect x="0" y="119" width="1040" height="1.5" class="fill-brand-line" />
	</svg>
</template>
