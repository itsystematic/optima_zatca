import { useCallback, useEffect, useRef, useState } from "react";
import { useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";

/**
 * The panel that says what this step is for.
 *
 * Every screen already states what to do. What none of them said is what the
 * step is *for*, and what happens if it is answered wrongly — which is the thing
 * whoever is doing the setup usually does not know, because they are rarely the
 * person who understands the regulation.
 *
 * Collapsed by default, and the choice is remembered across screens and reloads.
 *
 * Open by default cost about 130px at the top of every screen, which pushed the
 * continue button under the fold on the taller ones — help that hides the
 * control it is helping with is a poor trade. Closed, it costs a single row, the
 * step's title still says what the panel is about, and one click opens it on
 * every screen from then on. One preference, not one per step.
 */

const STORE_KEY = "optima_zatca.guide.open";

/** The steps that have a guide. Each needs `guide.<step>.title` and `.b1`–`.b3`. */
export type GuideStep =
	| "company"
	| "mode"
	| "scope"
	| "entity"
	| "registers"
	| "review"
	| "otp"
	| "progress"
	| "done";

const BULLETS = ["b1", "b2", "b3"] as const;

/**
 * Whether the panel starts open.
 *
 * Closed, unless this browser has said otherwise. Storage can throw outright — a
 * private window, a browser set to block site data — so a failure to read it is
 * treated as "no preference" rather than allowed to take the screen down with it.
 */
function storedOpen(): boolean {
	try {
		return window.localStorage.getItem(STORE_KEY) === "1";
	} catch {
		return false;
	}
}

function remember(open: boolean): void {
	try {
		window.localStorage.setItem(STORE_KEY, open ? "1" : "0");
	} catch {
		// a preference that cannot be saved is not worth failing a render over
	}
}

export function Guide({ step }: { step: GuideStep }) {
	const t = useT();
	const [open, setOpen] = useState(storedOpen);
	const body = useRef<HTMLDivElement>(null);

	const toggle = useCallback(() => {
		setOpen((was) => {
			remember(!was);
			return !was;
		});
	}, []);

	/**
	 * Animate to the content's own height rather than to a guessed one.
	 *
	 * `height: auto` cannot be transitioned, and a fixed max-height either clips
	 * the longest guide or leaves the shortest one closing against empty space.
	 * Measuring is the only version that is right for all nine.
	 */
	useEffect(() => {
		const el = body.current;
		if (!el) return;
		el.style.setProperty("--guide-h", `${el.scrollHeight}px`);
	}, [step, open, t]);

	return (
		<aside className="guide" aria-label={t("guide.label")}>
			<button
				type="button"
				className="guide__head"
				onClick={toggle}
				aria-expanded={open}
				aria-controls={`guide-${step}`}
			>
				<InfoMark />
				<span className="guide__title">{t(`guide.${step}.title` as MessageKey)}</span>
				<span className="guide__toggle">{open ? t("guide.hide") : t("guide.show")}</span>
				<Chevron open={open} />
			</button>

			<div
				id={`guide-${step}`}
				ref={body}
				className={`guide__body${open ? " guide__body--open" : ""}`}
				// hidden from the reading order when collapsed, not merely invisible
				aria-hidden={!open}
			>
				<ul className="guide__list">
					{BULLETS.map((b, i) => (
						<li
							key={b}
							className="guide__item"
							// each line arrives just after the one above it
							style={{ animationDelay: `${60 + i * 55}ms` }}
						>
							{t(`guide.${step}.${b}` as MessageKey)}
						</li>
					))}
				</ul>
			</div>
		</aside>
	);
}

function InfoMark() {
	return (
		<svg
			className="guide__mark"
			width="16"
			height="16"
			viewBox="0 0 16 16"
			fill="none"
			aria-hidden="true"
		>
			<circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4" />
			<path
				d="M8 7.2v4"
				stroke="currentColor"
				strokeWidth="1.6"
				strokeLinecap="round"
			/>
			<circle cx="8" cy="4.9" r="0.95" fill="currentColor" />
		</svg>
	);
}

function Chevron({ open }: { open: boolean }) {
	return (
		<svg
			className={`guide__chevron${open ? " guide__chevron--open" : ""}`}
			width="12"
			height="12"
			viewBox="0 0 12 12"
			fill="none"
			aria-hidden="true"
		>
			<path
				d="M2.5 4.5 6 8l3.5-3.5"
				stroke="currentColor"
				strokeWidth="1.6"
				strokeLinecap="round"
				strokeLinejoin="round"
			/>
		</svg>
	);
}
