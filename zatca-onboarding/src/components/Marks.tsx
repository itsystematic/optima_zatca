/**
 * The marks on the welcome footer, and the product's own.
 *
 * These are not the authorities' emblems. An official crest on a product screen
 * reads as accreditation by the body it belongs to, which is a claim this app is
 * not in a position to make — so each institution is drawn by what it *does*: a
 * seal that stamps, a register that records, a certificate that attests. Swap in
 * licensed artwork here if there is ever permission for it; nothing else needs to
 * change.
 *
 * Monoline on a 24 unit grid at the weight the wordmark uses, so the row reads as
 * one set rather than three logos that happen to be adjacent. They take their
 * colour from `currentColor`, so they follow the theme. The one exception is
 * `ITSystematicMark` below, which is the identity itself: real artwork, with
 * the gradient baked in.
 */

import logoUrl from "@/assets/it-logo.webp";

const STROKE = 1.75;

type MarkProps = { size?: number; title?: string };

function frame({ size = 30, title }: MarkProps) {
	return {
		width: size,
		height: size,
		viewBox: "0 0 24 24",
		fill: "none",
		stroke: "currentColor",
		strokeWidth: STROKE,
		strokeLinecap: "round" as const,
		strokeLinejoin: "round" as const,
		role: title ? ("img" as const) : undefined,
		"aria-hidden": title ? undefined : (true as const),
	};
}

/** The body that clears and reports: a seal, because it is what stamps a filing. */
export function TaxAuthorityMark(props: MarkProps) {
	return (
		<svg {...frame(props)}>
			{props.title && <title>{props.title}</title>}
			<circle cx="12" cy="10" r="6.2" />
			<circle cx="12" cy="10" r="3.1" />
			{/* the ribbon of a struck seal */}
			<path d="M8.6 15.4 7.2 21l4.8-2.2 4.8 2.2-1.4-5.6" />
		</svg>
	);
}

/** The commercial register: a bound ledger, which is what a CRN is an entry in. */
export function CommerceMark(props: MarkProps) {
	return (
		<svg {...frame(props)}>
			{props.title && <title>{props.title}</title>}
			<path d="M4 5.2A1.2 1.2 0 0 1 5.2 4h5.3A1.5 1.5 0 0 1 12 5.5v14a1.2 1.2 0 0 0-1.2-1.2H5.2A1.2 1.2 0 0 1 4 17.1V5.2Z" />
			<path d="M20 5.2A1.2 1.2 0 0 0 18.8 4h-5.3A1.5 1.5 0 0 0 12 5.5v14a1.2 1.2 0 0 1 1.2-1.2h5.6A1.2 1.2 0 0 0 20 17.1V5.2Z" />
			{/* two entries, because a register is a list */}
			<path d="M6.6 8.4h3M14.4 8.4h3" />
		</svg>
	);
}

/** The authority that issues the certificate: an attestation, sealed. */
export function CertificateAuthorityMark(props: MarkProps) {
	return (
		<svg {...frame(props)}>
			{props.title && <title>{props.title}</title>}
			<path d="M18.5 12.6V5.2A1.2 1.2 0 0 0 17.3 4H4.7A1.2 1.2 0 0 0 3.5 5.2v9.6A1.2 1.2 0 0 0 4.7 16h5.1" />
			<path d="M6.6 8h8M6.6 11.4h4.4" />
            {/* the rosette a certificate is signed under */}
			<circle cx="16.4" cy="17" r="3.1" />
			<path d="M14.6 19.6 13.9 22l2.5-1.1 2.5 1.1-.7-2.4" />
		</svg>
	);
}

/**
 * The product's own mark: the IT Systematic logo.
 *
 * The supplied artwork rather than a drawing of it. The mark is a hexagonal "IT"
 * monogram carrying a navy-to-magenta sweep, and the whole identity — every
 * brand token in `tokens.css` — is sampled from this file, so redrawing it in
 * markup would only introduce a second, slightly wrong version of the thing the
 * palette was taken from.
 *
 * Imported rather than referenced by URL so Vite fingerprints it and rewrites the
 * path for whichever base the app is served under; a hard-coded `/assets/...`
 * would be right in the bench and broken in the dev server.
 */
export function ITSystematicMark({ size = 26, title }: MarkProps) {
	return (
		<img
			src={logoUrl}
			width={size}
			height={size}
			alt={title ?? ""}
			// the logo is square and must never be stretched by a flex parent
			style={{ width: size, height: size, objectFit: "contain", flex: "none" }}
			// a decorative mark beside a wordmark that already says the name is
			// noise to a screen reader; one that stands alone is not
			aria-hidden={title ? undefined : true}
			draggable={false}
		/>
	);
}

/** Mark plus wordmark, for a footer or a header. */
export function ITSystematicLogo({ size = 22 }: { size?: number }) {
	return (
		<span className="brand">
			<ITSystematicMark size={size} title="IT Systematic" />
			<span className="brand__word" style={{ fontSize: size * 0.72 }}>
				Optima <span className="brand__word-accent">ZATCA</span>
			</span>
		</span>
	);
}
