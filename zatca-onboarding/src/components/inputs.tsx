import { useEffect, useId, useRef } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Field, Mark, cx } from "./primitives";
import { OTP_LENGTH, digitsOnly } from "@/lib/validation";

/**
 * Live form controls built on the `Field` shell, so a real input is
 * indistinguishable from the static one the artboards were drawn with.
 */

type TextFieldProps = {
	label?: ReactNode;
	labelMeta?: ReactNode;
	labelMetaTone?: "muted" | "req" | "mono";
	value: string;
	onChange: (value: string) => void;
	onBlur?: () => void;
	placeholder?: string;
	/** shown under the field when there is no error */
	hint?: ReactNode;
	/** shown under the field, in red, and reddens the border */
	error?: string | null;
	/** draws the green tick and greens the border */
	valid?: boolean;
	/** the confirmation line shown once `valid` */
	validHint?: ReactNode;
	mono?: boolean;
	arabic?: boolean;
	dir?: "rtl" | "ltr";
	locked?: boolean;
	maxLength?: number;
	/** restrict typing to digits, which is what most of these fields are */
	numeric?: boolean;
	/** renders "13 / 15" at the end of the control */
	counter?: string;
	trailing?: ReactNode;
	autoFocus?: boolean;
	style?: CSSProperties;
};

export function TextField({
	label,
	labelMeta,
	labelMetaTone,
	value,
	onChange,
	onBlur,
	placeholder,
	hint,
	error,
	valid,
	validHint,
	mono,
	arabic,
	dir,
	locked,
	maxLength,
	numeric,
	counter,
	trailing,
	autoFocus,
	style,
}: TextFieldProps) {
	const id = useId();
	const state = locked ? "locked" : error ? "err" : valid ? "ok" : "default";

	return (
		<Field
			label={label}
			htmlFor={id}
			labelMeta={labelMeta}
			labelMetaTone={labelMetaTone}
			state={state}
			mono={mono}
			arabic={arabic}
			dir={dir}
			hint={error ?? (valid && validHint ? validHint : hint)}
			hintTone={error ? "err" : valid && validHint ? "ok" : "muted"}
			style={style}
		>
			<input
				id={id}
				className="field__input"
				value={value}
				readOnly={locked}
				disabled={locked}
				placeholder={placeholder}
				maxLength={maxLength}
				autoFocus={autoFocus}
				inputMode={numeric ? "numeric" : undefined}
				onBlur={onBlur}
				onChange={(e) => onChange(numeric ? digitsOnly(e.target.value) : e.target.value)}
			/>
			{counter && <span className="field__count">{counter}</span>}
			{valid && !counter && <Mark kind="tick" size={16} font={10} />}
			{trailing}
		</Field>
	);
}

export function SelectField({
	label,
	value,
	onChange,
	options,
	placeholder = "Select…",
	hint,
	error,
	valid,
	validHint,
	locked,
	style,
}: {
	label?: ReactNode;
	value: string;
	onChange: (value: string) => void;
	options: string[];
	placeholder?: string;
	hint?: ReactNode;
	error?: string | null;
	valid?: boolean;
	validHint?: ReactNode;
	locked?: boolean;
	style?: CSSProperties;
}) {
	const id = useId();
	const state = locked ? "locked" : error ? "err" : valid ? "ok" : "default";

	return (
		<Field
			label={label}
			htmlFor={id}
			state={state}
			hint={error ?? (valid && validHint ? validHint : hint)}
			hintTone={error ? "err" : valid && validHint ? "ok" : "muted"}
			style={style}
		>
			<select
				id={id}
				className="field__select"
				value={value}
				disabled={locked}
				onChange={(e) => onChange(e.target.value)}
			>
				<option value="" disabled>
					{placeholder}
				</option>
				{options.map((o) => (
					<option key={o} value={o}>
						{o}
					</option>
				))}
			</select>
			{valid && <Mark kind="tick" size={16} font={10} />}
			<span className="field__caret">▾</span>
		</Field>
	);
}

/**
 * A text field that suggests known values without confining the operator to
 * them. The city list is whatever addresses already use, so the first register
 * in a new city would otherwise have nowhere to go.
 */
export function ComboField({
	label,
	value,
	onChange,
	onBlur,
	options,
	placeholder,
	hint,
	error,
	valid,
	style,
}: {
	label?: ReactNode;
	value: string;
	onChange: (value: string) => void;
	onBlur?: () => void;
	options: string[];
	placeholder?: string;
	hint?: ReactNode;
	error?: string | null;
	valid?: boolean;
	style?: CSSProperties;
}) {
	const id = useId();
	const listId = `${id}-options`;
	const state = error ? "err" : valid ? "ok" : "default";

	return (
		<Field
			label={label}
			htmlFor={id}
			state={state}
			hint={error ?? hint}
			hintTone={error ? "err" : "muted"}
			style={style}
		>
			<input
				id={id}
				className="field__input"
				list={listId}
				value={value}
				placeholder={placeholder}
				onBlur={onBlur}
				onChange={(e) => onChange(e.target.value)}
			/>
			<datalist id={listId}>
				{options.map((o) => (
					<option key={o} value={o} />
				))}
			</datalist>
			{valid && <Mark kind="tick" size={16} font={10} />}
			<span className="field__caret">▾</span>
		</Field>
	);
}

/**
 * Six segments that behave the way people expect: typing advances, backspace on
 * an empty box steps back, and pasting a whole code fills the row at once.
 */
export function OtpInput({
	value,
	onChange,
	label,
	digitLabel,
	autoFocus,
}: {
	value: string;
	onChange: (value: string) => void;
	/** names the whole group, e.g. "OTP for Riyadh — Head office" */
	label: string;
	/** names one segment; defaults to appending the position to `label` */
	digitLabel?: (n: number) => string;
	autoFocus?: boolean;
}) {
	const refs = useRef<(HTMLInputElement | null)[]>([]);
	const cells = Array.from({ length: OTP_LENGTH }, (_, i) => value[i] ?? "");

	useEffect(() => {
		if (autoFocus) refs.current[0]?.focus();
	}, [autoFocus]);

	const write = (next: string) => onChange(digitsOnly(next).slice(0, OTP_LENGTH));

	const setAt = (index: number, char: string) => {
		const next = cells.slice();
		next[index] = char;
		write(next.join(""));
		if (char && index < OTP_LENGTH - 1) refs.current[index + 1]?.focus();
	};

	return (
		<div className="otp" role="group" aria-label={label}>
			{cells.map((char, i) => (
				<input
					key={i}
					ref={(el) => {
						refs.current[i] = el;
					}}
					className="otp__cell"
					data-filled={Boolean(char)}
					value={char}
					inputMode="numeric"
					autoComplete="one-time-code"
					aria-label={digitLabel ? digitLabel(i + 1) : `${label} ${i + 1}`}
					onChange={(e) => {
						const typed = digitsOnly(e.target.value);
						// a multi-character value means a paste landed in this box
						if (typed.length > 1) {
							write(value.slice(0, i) + typed);
							refs.current[Math.min(OTP_LENGTH - 1, i + typed.length)]?.focus();
							return;
						}
						setAt(i, typed.slice(-1));
					}}
					onKeyDown={(e) => {
						if (e.key === "Backspace" && !char && i > 0) {
							e.preventDefault();
							setAt(i - 1, "");
							refs.current[i - 1]?.focus();
						}
						if (e.key === "ArrowLeft" && i > 0) refs.current[i - 1]?.focus();
						if (e.key === "ArrowRight" && i < OTP_LENGTH - 1) refs.current[i + 1]?.focus();
					}}
					onPaste={(e) => {
						e.preventDefault();
						const pasted = digitsOnly(e.clipboardData.getData("text"));
						write(value.slice(0, i) + pasted);
						refs.current[Math.min(OTP_LENGTH - 1, i + pasted.length)]?.focus();
					}}
				/>
			))}
		</div>
	);
}

/**
 * A card that behaves as a radio: whole surface clickable, keyboard operable.
 *
 * Deliberately a `div` rather than a `button` — one of these cards contains its
 * own text field, and a form control nested inside a button is invalid markup
 * that browsers handle inconsistently.
 */
export function ChoiceCard({
	selected,
	onSelect,
	children,
	style,
	className,
	disabled = false,
}: {
	selected: boolean;
	onSelect: () => void;
	children: ReactNode;
	style?: CSSProperties;
	className?: string;
	/** A choice this company cannot make. The card still reads; it just cannot be taken. */
	disabled?: boolean;
}) {
	if (disabled) {
		return (
			<div
				role="radio"
				aria-checked={false}
				aria-disabled
				className={["choice", "choice--disabled", className].filter(Boolean).join(" ")}
				style={style}
			>
				{children}
			</div>
		);
	}
	return (
		<div
			role="radio"
			aria-checked={selected}
			tabIndex={0}
			onClick={onSelect}
			onKeyDown={(e) => {
				if (e.key === " " || e.key === "Enter") {
					e.preventDefault();
					onSelect();
				}
			}}
			className={cx("choice", className)}
			style={style}
		>
			{children}
		</div>
	);
}
