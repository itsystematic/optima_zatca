import flagUrl from "@/assets/saudi.webp";

/**
 * A Riyadh horizon along the foot of the welcome card.
 *
 * The interface this replaced opened on a photographic banner with a skyline
 * across the bottom, and losing it entirely made the first screen read as though
 * it belonged to nowhere in particular. This is that idea rebuilt as artwork the
 * page owns: it takes its colours from the brand tokens, so it cannot clash with
 * a palette change, and it costs a few hundred bytes rather than a megabyte of
 * JPEG.
 *
 * Drawn in two tinted layers — a pale one set back, a stronger one in front — so
 * it reads as depth rather than as a stencil. Everything is deliberately faint:
 * the one thing on this screen that should hold the eye is the button.
 *
 * The flag is the real artwork rather than a drawing of it, which is what lets
 * it sit at the scale of the buildings around it instead of having to be large
 * enough for hand-drawn script to be legible. See `SaudiFlag` below.
 */
export function Skyline({ height = 132 }: { height?: number }) {
	return (
		<svg
			viewBox="0 0 1040 132"
			width="100%"
			height={height}
			preserveAspectRatio="xMidYMax slice"
			// wholly decorative: the sentence above it already says where this is
			aria-hidden="true"
			focusable="false"
			className="skyline"
			style={{ display: "block" }}
		>
			{/* ── back layer: the city that is not the subject ───────────────── */}
			<g fill="var(--brand-line-2)">
				<rect x="60" y="80" width="34" height="40" />
				<rect x="100" y="90" width="26" height="30" />
				<rect x="132" y="72" width="30" height="48" />
				<rect x="262" y="76" width="26" height="44" />
				<rect x="294" y="86" width="34" height="34" />
				<rect x="336" y="66" width="24" height="54" />
				<rect x="500" y="78" width="30" height="42" />
				<rect x="536" y="64" width="22" height="56" />
				<rect x="700" y="82" width="32" height="38" />
				<rect x="738" y="70" width="24" height="50" />
				<rect x="856" y="84" width="30" height="36" />
				<rect x="892" y="92" width="24" height="28" />
			</g>

			{/* ── front layer: the landmarks ─────────────────────────────────── */}
			<g fill="var(--brand-line)" opacity="0.85">
				{/* Al Faisaliah — a slender taper, the glass ball below the spire */}
				<path d="M190 120 L198.6 40 L201.4 40 L210 120 Z" />
				<circle cx="200" cy="47" r="8" />
				<rect x="199.2" y="12" width="1.6" height="28" />

				{/* Kingdom Centre — a solid slab that splits into two arms near the
				    top, the opening between them closed by the crowning arch. Drawn
				    as one path with an enclosed hole, so the gap cannot leak to the
				    ground and turn the tower into a bridge. */}
				<path
					fillRule="evenodd"
					d="M404 120 L456 120 L456 44 C456 18 404 18 404 44 Z
					   M418 78 L442 78 L442 50 C442 34 418 34 418 50 Z"
				/>
				{/* the sky bridge across the opening */}
				<rect x="416" y="46" width="28" height="4" />

				{/* a mosque: dome between two minarets */}
				<rect x="586" y="56" width="6" height="64" />
				<circle cx="589" cy="53" r="5" />
				<rect x="588.2" y="34" width="1.6" height="16" />
				<rect x="600" y="98" width="46" height="22" />
				<path d="M600 98 A23 23 0 0 1 646 98 Z" />
				<rect x="622.2" y="64" width="1.6" height="14" />
				<rect x="652" y="56" width="6" height="64" />
				<circle cx="655" cy="53" r="5" />
				<rect x="654.2" y="34" width="1.6" height="16" />

				{/* a stepped tower and its mast */}
				<path d="M772 120 L772 60 L784 60 L784 44 L800 44 L800 60 L812 60 L812 120 Z" />
				<rect x="791.2" y="20" width="1.6" height="26" />
			</g>

			{/* Palms are stroked rather than filled: a frond is a line that arches
			    up from the crown and droops at the tip, which no filled blob does. */}
			<g
				fill="none"
				stroke="var(--brand-line)"
				strokeWidth="2.4"
				strokeLinecap="round"
				opacity="0.85"
			>
				<PalmTree x={34} y={120} scale={1} />
				<PalmTree x={846} y={120} scale={0.82} />
			</g>

			{/* ── the flag ───────────────────────────────────────────────────── */}
			<SaudiFlag x={928} y={38} width={82} />

			{/* the ground the whole city stands on */}
			<rect x="0" y="119" width="1040" height="1.5" fill="var(--brand-line)" />
		</svg>
	);
}

/**
 * A date palm, drawn from the crown outwards.
 *
 * Seven fronds, each a curve that rises from the crown before its tip falls
 * away — the shape that distinguishes a palm from every other tree in
 * silhouette. The trunk leans very slightly, because a straight one reads as a
 * pole.
 */
function PalmTree({ x, y, scale = 1 }: { x: number; y: number; scale?: number }) {
	return (
		<g transform={`translate(${x} ${y}) scale(${scale})`}>
			<path d="M1.5 0 C0.5 -14 -0.5 -28 -0.5 -42" />
			<path d="M-0.5 -42 C -8 -52 -20 -54 -28 -47" />
			<path d="M-0.5 -42 C 7 -52 19 -54 27 -47" />
			<path d="M-0.5 -42 C -6 -54 -14 -61 -21 -62" />
			<path d="M-0.5 -42 C 5 -54 13 -61 20 -62" />
			<path d="M-0.5 -42 C -3 -55 -7 -64 -11 -69" />
			<path d="M-0.5 -42 C 2 -55 6 -64 10 -69" />
			<path d="M-0.5 -42 C -0.5 -54 -0.5 -63 0.5 -70" />
		</g>
	);
}


/**
 * The flag of the Kingdom of Saudi Arabia.
 *
 * The supplied artwork, not a drawing of it. An earlier version of this file
 * drew the field, the shahada and the sword by hand; the shahada is scripture
 * set in Thuluth, which no web font carries, and the sword is a slender sabre
 * with a particular hilt that a few SVG primitives do not reproduce. Both came
 * out wrong. A national flag is not a thing to approximate, so the real image is
 * embedded instead.
 *
 * Placed with `<image>` inside the same SVG as the rest of the horizon so it
 * scales with the viewBox, and imported rather than referenced by URL so Vite
 * fingerprints it and rewrites the path for whichever base the app is served
 * under.
 */
function SaudiFlag({ x, y, width }: { x: number; y: number; width: number }) {
	// the official proportion is 2:3
	const height = (width * 2) / 3;

	return (
		<g transform={`translate(${x} ${y})`}>
			{/* the pole, running down to the ground line */}
			<rect x="-5" y="-5" width="2.4" height={132 - y + 5} fill="var(--brand-line-3)" />
			<circle cx="-3.8" cy="-7" r="2.4" fill="var(--brand-line-3)" />

			<image
				href={flagUrl}
				width={width}
				height={height}
				preserveAspectRatio="xMidYMid meet"
			/>
		</g>
	);
}
