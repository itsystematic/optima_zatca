import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

/**
 * One burst, when a registration finishes cleanly.
 *
 * Drawn on a canvas rather than pulled from a library: it is a couple of hundred
 * rectangles for a few seconds, and a dependency for that would cost more than it
 * is worth in a bundle a tax app has to serve from a Frappe site.
 *
 * A burst, never a loop. The animation frame stops when the last piece leaves the
 * viewport, so a screen left open does not sit repainting for the rest of the day.
 * Honours `prefers-reduced-motion` by not running at all, and the canvas never
 * takes pointer events, so nothing underneath becomes unclickable.
 */

const PIECES = 170;
const GRAVITY = 0.13;
const DRAG = 0.994;
const FADE_AFTER_MS = 2600;
const MAX_MS = 6000;

export type Piece = {
	x: number;
	y: number;
	vx: number;
	vy: number;
	size: number;
	spin: number;
	angle: number;
	colour: string;
};

/** Brand first, then the accents already used for a settled state. */
const COLOURS = ["#73006c", "#9e0084", "#d8b45a", "#c98fbf", "#01002b"];

export function build(width: number, random: () => number): Piece[] {
	return Array.from({ length: PIECES }, (_, index) => {
		/*
		 * Two side vents throwing inwards, and every third piece falling anywhere
		 * across the width.
		 *
		 * The vents alone kept the middle of the card clear, which read as two
		 * thin jets at the margins rather than as a celebration — on a wide screen
		 * most of the viewport had nothing in it. The full-width third is what
		 * makes the burst cover the screen; it passes over the card for about a
		 * second and the card is still legible through it, because the pieces are
		 * small and moving.
		 */
		const vented = index % 3 !== 2;
		const fromLeft = random() < 0.5;
		const across = random();
		const originX = vented ? (fromLeft ? width * 0.12 : width * 0.88) : across * width;
		const aim = fromLeft ? 1 : -1;
		return {
			x: originX,
			// staggered well above the fold, so pieces keep arriving instead of
			// falling as one flat sheet
			y: -20 - random() * 320,
			vx: vented ? aim * (1.1 + random() * 4.2) : (random() - 0.5) * 2,
			vy: 1.8 + random() * 2.8,
			size: 8 + random() * 12,
			spin: (random() - 0.5) * 0.3,
			angle: random() * Math.PI,
			colour: COLOURS[Math.floor(random() * COLOURS.length)],
		};
	});
}

export function Confetti({ run }: { run: boolean }) {
	const canvasRef = useRef<HTMLCanvasElement | null>(null);

	/*
	 * Firing is governed by the `run` dependency alone.
	 *
	 * There used to be a `fired` ref here as well, to stop the burst repeating.
	 * It did more than that: StrictMode mounts an effect, tears it down and
	 * mounts it again, so the first pass set the flag and started the loop, the
	 * teardown cancelled the animation frame, and the second pass returned early
	 * on the flag it had just set. The canvas was sized and then left blank —
	 * meaning nobody saw the confetti in development at all.
	 *
	 * The dependency array already does the job: the effect runs when `run`
	 * becomes true and not on re-renders while it stays true.
	 */
	useEffect(() => {
		if (!run) return;
		const canvas = canvasRef.current;
		if (!canvas) return;

		// a celebration is decoration; someone who asked for less motion gets none
		if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

		const context = canvas.getContext("2d");
		if (!context) return;

		const ratio = window.devicePixelRatio || 1;
		const width = canvas.clientWidth;
		const height = canvas.clientHeight;
		canvas.width = width * ratio;
		canvas.height = height * ratio;
		context.scale(ratio, ratio);

		const pieces = build(width, Math.random);
		const started = performance.now();
		let frame = 0;

		const tick = (now: number) => {
			const elapsed = now - started;
			context.clearRect(0, 0, width, height);

			let visible = 0;
			for (const piece of pieces) {
				piece.vy += GRAVITY;
				piece.vx *= DRAG;
				piece.x += piece.vx;
				piece.y += piece.vy;
				piece.angle += piece.spin;

				if (piece.y - piece.size > height) continue;
				visible += 1;

				context.save();
				context.translate(piece.x, piece.y);
				context.rotate(piece.angle);
				context.globalAlpha =
					elapsed < FADE_AFTER_MS
						? 1
						: Math.max(0, 1 - (elapsed - FADE_AFTER_MS) / (MAX_MS - FADE_AFTER_MS));
				context.fillStyle = piece.colour;
				context.fillRect(-piece.size / 2, -piece.size / 3, piece.size, piece.size / 1.5);
				context.restore();
			}

			// stop on either condition: everything has fallen, or it has gone on long
			// enough. Neither alone is sufficient — a piece can hang on the drag.
			if (visible > 0 && elapsed < MAX_MS) {
				frame = requestAnimationFrame(tick);
				return;
			}
			context.clearRect(0, 0, width, height);
		};

		frame = requestAnimationFrame(tick);
		return () => {
			cancelAnimationFrame(frame);
			context.clearRect(0, 0, width, height);
		};
	}, [run]);

	/*
	 * Rendered into `document.body` rather than where it is written.
	 *
	 * `position: fixed` is relative to the viewport only while no ancestor has a
	 * transform; one that does becomes the containing block instead. The screen's
	 * entry animation transforms `.page__body`, which also scrolls — so the canvas
	 * was sized to that box and clipped by it, and the burst went off inside a
	 * container nobody could see it in. A portal puts the overlay outside every
	 * one of those, which is what a viewport overlay needs.
	 */
	return createPortal(
		<canvas
			ref={canvasRef}
			aria-hidden
			style={{
				position: "fixed",
				inset: 0,
				width: "100vw",
				height: "100vh",
				pointerEvents: "none",
				// above the page and its chrome, below the environment popover
				zIndex: 8500,
			}}
		/>,
		document.body,
	);
}
