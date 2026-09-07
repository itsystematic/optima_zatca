import type { CSSProperties, ReactNode } from "react";

const cx = (...parts: (string | false | undefined | null)[]) => parts.filter(Boolean).join(" ");

/* ── Type ───────────────────────────────────────────────────────────────── */

export function Eyebrow({
	children,
	tone = "muted",
	size = "sm",
	style,
}: {
	children: ReactNode;
	tone?: "muted" | "brand";
	size?: "sm" | "lg";
	style?: CSSProperties;
}) {
	return (
		<div
			className={cx("eyebrow", tone === "brand" && "eyebrow--brand", size === "lg" && "eyebrow--lg")}
			style={style}
		>
			{children}
		</div>
	);
}

export function Rule({ strong = false, style }: { strong?: boolean; style?: CSSProperties }) {
	return <div className={cx("rule", strong && "rule--strong")} style={style} />;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */

type BtnProps = {
	children: ReactNode;
	variant?: "primary" | "secondary" | "ghost";
	size?: "md" | "sm" | "lg";
	/** greys the button out and blocks the click, keeping the disabled treatment */
	disabled?: boolean;
	/** swaps the label for a spinner while a mutation is in flight */
	busy?: boolean;
	onClick?: () => void;
	type?: "button" | "submit";
	title?: string;
	style?: CSSProperties;
};

export function Btn({
	children,
	variant = "primary",
	size = "md",
	disabled = false,
	busy = false,
	onClick,
	type = "button",
	title,
	style,
}: BtnProps) {
	const blocked = disabled || busy;
	return (
		<button
			type={type}
			title={title}
			onClick={blocked ? undefined : onClick}
			data-busy={busy || undefined}
			aria-busy={busy || undefined}
			className={cx(
				"btn",
				`btn--${disabled && variant === "primary" ? "disabled" : variant}`,
				size !== "md" && `btn--${size}`,
			)}
			style={style}
			disabled={blocked}
		>
			{children}
		</button>
	);
}

/* ── Marks ──────────────────────────────────────────────────────────────── */

type MarkKind = "tick" | "tick-solid" | "fail" | "idle" | "brand" | "pending" | "square";

const defaultGlyph: Partial<Record<MarkKind, string>> = {
	tick: "✓",
	"tick-solid": "✓",
	square: "✓",
	fail: "!",
};

/**
 * The small status disc used everywhere: green tick, red bang, dashed
 * placeholder, or a plain tinted dot for un-run steps.
 */
export function Mark({
	kind = "tick",
	size = 18,
	font,
	children,
	style,
}: {
	kind?: MarkKind;
	size?: number;
	font?: number;
	children?: ReactNode;
	style?: CSSProperties;
}) {
	return (
		<span
			className={cx("mark", `mark--${kind}`)}
			style={{ width: size, height: size, fontSize: font ?? Math.round(size * 0.56), ...style }}
		>
			{children ?? defaultGlyph[kind] ?? null}
		</span>
	);
}

export function Spinner({ size = 22 }: { size?: number }) {
	return <span className="spinner" style={{ width: size, height: size }} />;
}

export function Radio({ on = false }: { on?: boolean }) {
	return <span className={cx("radio", on && "radio--on")} />;
}

export function Checkbox({ size = 18, style }: { size?: number; style?: CSSProperties }) {
	return <span className="checkbox" style={{ width: size, height: size, ...style }} />;
}

/* ── Chips ──────────────────────────────────────────────────────────────── */

export function Chip({
	children,
	tone = "brand",
	pill = false,
	style,
}: {
	children: ReactNode;
	tone?: "brand" | "ok" | "outline" | "ribbon";
	pill?: boolean;
	style?: CSSProperties;
}) {
	return (
		<span
			className={cx("chip", tone !== "brand" && `chip--${tone}`, pill && "chip--pill")}
			style={style}
		>
			{children}
		</span>
	);
}

/** Rule with a centred pill — marks a section that just became available. */
export function UnlockRule({ children }: { children: ReactNode }) {
	return (
		<div className="unlock">
			<span>{children}</span>
		</div>
	);
}

/* ── Fields ─────────────────────────────────────────────────────────────── */

type FieldState = "default" | "ok" | "err" | "locked";

export function Field({
	label,
	htmlFor,
	labelMeta,
	labelMetaTone = "muted",
	hint,
	hintTone = "muted",
	state = "default",
	focus = false,
	mono = false,
	arabic = false,
	dir,
	children,
	style,
}: {
	label?: ReactNode;
	htmlFor?: string;
	labelMeta?: ReactNode;
	labelMetaTone?: "muted" | "req" | "mono";
	hint?: ReactNode;
	hintTone?: "muted" | "ok" | "err";
	state?: FieldState;
	focus?: boolean;
	mono?: boolean;
	arabic?: boolean;
	dir?: "rtl" | "ltr";
	children: ReactNode;
	style?: CSSProperties;
}) {
	return (
		<div className="field" style={style}>
			{label != null && (
				<div className="field__labelrow">
					<label
						htmlFor={htmlFor}
						className={cx("field__label", state === "locked" && "field__label--muted")}
					>
						{label}
					</label>
					{labelMeta != null && (
						<span
							className={cx(
								"field__meta",
								labelMetaTone !== "muted" && `field__meta--${labelMetaTone}`,
							)}
						>
							{labelMeta}
						</span>
					)}
				</div>
			)}
			<div
				dir={dir}
				className={cx(
					"field__control",
					state !== "default" && `field__control--${state}`,
					focus && "field__control--focus",
					mono && "field__control--num",
					arabic && "field__control--ar",
				)}
			>
				{children}
			</div>
			{hint != null &&
				(hintTone === "err" ? (
					<div className="field__hint--err">
						<Mark kind="fail" size={14} font={10} style={{ marginTop: 2 }} />
						<span>{hint}</span>
					</div>
				) : (
					<div className={cx("field__hint", hintTone === "ok" && "field__hint--ok")}>{hint}</div>
				))}
		</div>
	);
}

/** Convenience: the value + green tick pairing used by every validated field. */
export function ValidValue({ children }: { children: ReactNode }) {
	return (
		<>
			<div className="field__value">{children}</div>
			<Mark kind="tick" size={16} font={10} />
		</>
	);
}

export { cx };
