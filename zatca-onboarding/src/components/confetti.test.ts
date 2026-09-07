import { describe, expect, it } from "vitest";
import { build } from "./Confetti";

/** A deterministic stand-in for Math.random, so the geometry can be asserted. */
function sequence(values: number[]): () => number {
	let i = 0;
	return () => values[i++ % values.length];
}

describe("where the pieces come from", () => {
	it("covers the whole width, not just the two margins", () => {
		// The vents alone left the middle of a wide screen empty, which read as two
		// thin jets rather than a celebration. Every third piece now falls anywhere.
		const pieces = build(1000, Math.random);
		const middle = pieces.filter((piece) => piece.x > 300 && piece.x < 700);
		expect(middle.length).toBeGreaterThan(0);
	});

	it("still throws most of them from the two side vents", () => {
		const pieces = build(1000, Math.random);
		const vented = pieces.filter((piece) => Math.min(piece.x, 1000 - piece.x) <= 150);
		// two of every three, so the shape is still a burst from the edges
		expect(vented.length).toBeGreaterThan(pieces.length / 2);
	});

	it("aims each vented piece away from the edge it came from", () => {
		// first value < 0.5 puts it on the left, which must travel rightwards
		const [left] = build(1000, sequence([0.1, 0.5, 0.5, 0.5, 0.5, 0.5]));
		expect(left.x).toBeCloseTo(120);
		expect(left.vx).toBeGreaterThan(0);

		const [right] = build(1000, sequence([0.9, 0.5, 0.5, 0.5, 0.5, 0.5]));
		expect(right.x).toBeCloseTo(880);
		expect(right.vx).toBeLessThan(0);
	});

	it("starts every piece above the viewport, so none appears mid-air", () => {
		for (const piece of build(800, Math.random)) {
			expect(piece.y).toBeLessThan(0);
		}
	});

	it("always sends them downwards, so the burst cannot hang", () => {
		for (const piece of build(800, Math.random)) {
			expect(piece.vy).toBeGreaterThan(0);
		}
	});

	it("picks colours from the palette and nothing else", () => {
		const palette = new Set(["#73006c", "#9e0084", "#d8b45a", "#c98fbf", "#01002b"]);
		for (const piece of build(800, Math.random)) {
			expect(palette).toContain(piece.colour);
		}
	});

	it("gives every piece a drawable size", () => {
		for (const piece of build(800, Math.random)) {
			expect(piece.size).toBeGreaterThan(0);
		}
	});
});
