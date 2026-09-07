import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { Address, Problem, Register, RegisterInput, Setup } from "@/api";
import { Page } from "@/components/Page";
import { ComboField, TextField } from "@/components/inputs";
import { FormError } from "@/components/FormError";
import { Btn, Chip, Eyebrow, Mark, Rule, UnlockRule } from "@/components/primitives";
import { Stepper } from "@/components/Stepper";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { useProblemText, serverFieldErrors } from "@/lib/errors";
import { ADDRESS_RULES, CRN_LENGTH, crnProblem, registerNameProblem } from "@/lib/validation";
import {
	useAddRegister,
	useCities,
	useRemoveRegister,
	useSetup,
	useUpdateRegister,
} from "@/queries/setup";
import { paths } from "./paths";

const PHASE_KEY: Record<string, MessageKey> = {
	phase_1: "mode.phase1.title",
	phase_2: "mode.phase2.title",
};

/* ── Form state ─────────────────────────────────────────────────────────── */

type Values = { registerName: string; crn: string } & Omit<Address, "country">;

const BLANK: Values = {
	registerName: "",
	crn: "",
	buildingNumber: "",
	street: "",
	district: "",
	city: "",
	postalCode: "",
	additionalNumber: "",
	vatGroupNumber: "",
};

function toValues(register: Register): Values {
	const { country: _country, ...address } = register.address;
	return { registerName: register.registerName, crn: register.crn, ...address };
}

function toInput(values: Values): RegisterInput {
	const { registerName, crn, ...address } = values;
	return { registerName, crn, address };
}

/**
 * The register form's own rules. Identity first: until the register is named and
 * its number is well-formed and unused, the address grid stays folded away.
 */
function useRegisterForm(initial: Values, takenCrns: string[]) {
	const [values, setValues] = useState<Values>(initial);
	const [touched, setTouched] = useState<Record<string, boolean>>({});

	const set =
		<K extends keyof Values>(key: K) =>
		(value: Values[K]) =>
			setValues((v) => ({ ...v, [key]: value }));
	const touch = (key: keyof Values) => () => setTouched((prev) => ({ ...prev, [key]: true }));

	const problems = useMemo(() => {
		const crn = crnProblem(values.crn);
		const duplicate =
			!crn && takenCrns.includes(values.crn) ? { key: "validation.crn.duplicate" } : null;

		return {
			registerName: registerNameProblem(values.registerName),
			crn: crn ?? duplicate,
			buildingNumber: ADDRESS_RULES.buildingNumber(values.buildingNumber),
			street: ADDRESS_RULES.street(values.street),
			district: ADDRESS_RULES.district(values.district),
			city: ADDRESS_RULES.city(values.city),
			postalCode: ADDRESS_RULES.postalCode(values.postalCode),
			additionalNumber: ADDRESS_RULES.additionalNumber(values.additionalNumber),
			vatGroupNumber: ADDRESS_RULES.vatGroupNumber(values.vatGroupNumber),
		} satisfies Record<keyof Values, Problem>;
	}, [values, takenCrns]);

	const identityDone = !problems.registerName && !problems.crn;
	const complete = Object.values(problems).every((p) => p === null);

	return {
		values,
		set,
		touch,
		touched,
		setTouched,
		problems,
		identityDone,
		complete,
		reset: (next: Values = BLANK) => {
			setValues(next);
			setTouched({});
		},
	};
}

type FormApi = ReturnType<typeof useRegisterForm>;

/* ── Route ──────────────────────────────────────────────────────────────── */

/** 06 / 07 — the register step, in its single and multi-branch shapes. */
export function Registers() {
	const { data: setup } = useSetup();
	if (!setup) return null;
	return setup.scope === "single" ? <SingleRegister setup={setup} /> : <MultiRegister setup={setup} />;
}

/* ── Single registration (artboard 06) ──────────────────────────────────── */

function SingleRegister({ setup }: { setup: Setup }) {
	const navigate = useNavigate();
	const t = useT();
	const existing = setup.registers[0];
	const form = useRegisterForm(existing ? toValues(existing) : BLANK, []);
	const add = useAddRegister();
	const update = useUpdateRegister();
	const saving = add.isPending || update.isPending;
	const error = add.error ?? update.error;

	const save = () => {
		form.setTouched(allTouched());
		if (!form.complete) return;
		const input = toInput(form.values);
		const done = { onSuccess: () => navigate(paths.review) };
		if (existing) update.mutate({ id: existing.id, input }, done);
		else add.mutate(input, done);
	};

	return (
		<Page guide="registers" width={1040}>
			<div className="col" style={{ gap: 24 }}>
				<Stepper
					size="md"
					steps={[
						{ badge: "1", label: t("steps.entity"), state: "done" },
						{ badge: "2", label: t("steps.registers"), state: "current" },
						{ badge: "3", label: t("steps.review"), state: "idle" },
						{ badge: "4", label: t("steps.register"), state: "idle" },
					]}
				/>

				<div className="card col" style={{ padding: "24px 32px", gap: 18 }}>
					<div className="col" style={{ gap: 6 }}>
						<h2 className="title" style={{ fontSize: 21, letterSpacing: "-.015em" }}>
							{t("registers.title")}
						</h2>
						<div style={{ fontSize: 13.5, color: "var(--muted)" }}>{t("registers.body")}</div>
					</div>

					<FormError error={error} />
					<IdentityFields form={form} error={error} gap={22} />

					{form.identityDone ? (
						<>
							<UnlockRule>{t("registers.unlocked.both")}</UnlockRule>
							<AddressFields
								form={form}
								error={error}
								heading={
									<div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
										<h3 className="title" style={{ fontSize: 16 }}>
											{t("registers.address.title")}
										</h3>
										<div style={{ fontSize: 12.5, color: "var(--muted)" }}>
											{t("registers.address.filedUnder", { crn: form.values.crn })}
										</div>
									</div>
								}
							/>
						</>
					) : (
						<LockedNotice />
					)}

					<Rule />
					<div className="actions">
						<Btn onClick={save} busy={saving} disabled={!form.complete}>
							{t("registers.saveContinue")}
						</Btn>
						<Btn variant="secondary" onClick={() => navigate(paths.entity)}>
							{t("common.back")}
						</Btn>
						<div className="grow" />
						<div style={{ fontSize: 12.5, color: "var(--muted-2)" }}>
							{t("registers.singleFooter")}
						</div>
					</div>
				</div>
			</div>
		</Page>
	);
}

/* ── Multiple registers (artboard 07) ───────────────────────────────────── */

function MultiRegister({ setup }: { setup: Setup }) {
	const navigate = useNavigate();
	const t = useT();
	const [params, setParams] = useSearchParams();
	const editId = params.get("edit");
	const editing = setup.registers.find((r) => r.id === editId) ?? null;

	const takenCrns = setup.registers.filter((r) => r.id !== editId).map((r) => r.crn);
	const form = useRegisterForm(editing ? toValues(editing) : BLANK, takenCrns);
	const [expandedId, setExpandedId] = useState<string | null>(setup.registers[1]?.id ?? null);

	const add = useAddRegister();
	const update = useUpdateRegister();
	const remove = useRemoveRegister();
	const saving = add.isPending || update.isPending;
	const error = add.error ?? update.error ?? remove.error;

	const expected = setup.expectedRegisters;
	const saved = setup.registers.length;
	const position = editing ? editing.index : saved + 1;

	const persist = (after: "review" | "another") => {
		form.setTouched(allTouched());
		if (!form.complete) return;
		const input = toInput(form.values);
		const onSuccess = () => {
			if (after === "another") {
				form.reset();
				if (editId) setParams({}, { replace: true });
			} else {
				navigate(paths.review);
			}
		};
		if (editing) update.mutate({ id: editing.id, input }, { onSuccess });
		else add.mutate(input, { onSuccess });
	};

	const startEdit = (id: string) => {
		const target = setup.registers.find((r) => r.id === id);
		// a live register is fixed; the server refuses the write either way
		if (!target || target.status === "live") return;
		form.reset(toValues(target));
		setParams({ edit: id }, { replace: true });
	};

	const startNew = () => {
		form.reset();
		setParams({}, { replace: true });
	};

	return (
		<Page guide="registers" width={1160} status={t("registers.autosaving")} pad="28px 40px">
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "320px 1fr",
					gap: 22,
					alignItems: "start",
				}}
			>
				<div className="card col" style={{ overflow: "hidden" }}>
					<div
						className="col"
						style={{ padding: "18px 18px 14px", gap: 5, borderBottom: "1px solid var(--line-hair)" }}
					>
						<Eyebrow>{t("registers.added")}</Eyebrow>
						<div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
							<div style={{ fontSize: 22, fontWeight: 600 }}>{saved}</div>
							<div style={{ fontSize: 12.5, color: "var(--muted)" }}>
								{expected
									? t("registers.ofExpected", { count: expected })
									: t("registers.countOnly", { count: saved })}
							</div>
						</div>
						{expected ? (
							<div className="meter meter--thin" style={{ marginTop: 6 }}>
								<div
									className="meter__brand"
									style={{ width: `${Math.min(100, (saved / expected) * 100)}%` }}
								/>
							</div>
						) : null}
					</div>

					<div className="col">
						{setup.registers.map((r) => (
							<BankedRow
								key={r.id}
								register={r}
								phase={setup.phase}
								open={expandedId === r.id}
								editing={editId === r.id}
								onToggle={() => setExpandedId((id) => (id === r.id ? null : r.id))}
								onEdit={() => startEdit(r.id)}
								onRemove={() => remove.mutate(r.id)}
								removing={remove.isPending}
							/>
						))}

						{!editing && (
							<div
								className="row"
								style={{
									padding: "14px 18px",
									borderBottom: "1px solid var(--line-hair)",
									gap: 11,
									background: "var(--brand-tint-2)",
								}}
							>
								<Mark kind="pending" size={18} />
								<div className="col" style={{ flex: 1, gap: 2 }}>
									<div style={{ fontSize: 13, fontWeight: 600, color: "var(--brand)" }}>
										{t("registers.rowInProgress", { n: position })}
									</div>
									<div style={{ fontSize: 11, color: "var(--brand-soft)" }}>
										{t("registers.fillingIn")}
									</div>
								</div>
							</div>
						)}
					</div>

					<div className="col" style={{ padding: "16px 18px", gap: 10 }}>
						<button
							type="button"
							onClick={startNew}
							style={{
								border: "1.5px dashed var(--brand-line)",
								borderRadius: 8,
								padding: 12,
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								gap: 8,
								color: "var(--brand)",
								fontSize: 13,
								fontWeight: 600,
								background: "var(--surface)",
								cursor: "pointer",
							}}
						>
							{t("registers.addAnother")}
						</button>
						<div style={{ fontSize: 11.5, lineHeight: 1.5, color: "var(--muted-2)" }}>
							{t("registers.addNote")}
						</div>
					</div>
				</div>

				<div className="card col" style={{ padding: "28px 32px", gap: 22 }}>
					<div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
						<div className="col" style={{ gap: 5, flex: 1 }}>
							<h2 className="title" style={{ fontSize: 20, letterSpacing: "-.015em" }}>
								{editing
									? t("registers.headingEdit", { n: editing.index })
									: expected
										? t("registers.headingOf", { n: position, total: expected })
										: t("registers.heading", { n: position })}
							</h2>
							<div style={{ fontSize: 13, color: "var(--muted)" }}>{t("registers.stepLabel")}</div>
						</div>
						<Chip tone="outline">
							{t(editing ? "registers.chipEditing" : "registers.chipDraft")}
						</Chip>
					</div>

					<FormError error={error} />
					<IdentityFields form={form} error={error} gap={20} unusedHint />

					{form.identityDone ? (
						<>
							<UnlockRule>{t("registers.unlocked.address")}</UnlockRule>
							<AddressFields form={form} error={error} compact />
						</>
					) : (
						<LockedNotice />
					)}

					<Rule />
					<div className="actions" style={{ gap: 12 }}>
						<Btn
							onClick={() => persist("review")}
							busy={saving}
							disabled={!form.complete}
							style={{ padding: "12px 22px" }}
						>
							{t(editing ? "registers.saveChanges" : "registers.save")}
						</Btn>
						<Btn
							variant="secondary"
							onClick={() => persist("another")}
							disabled={!form.complete || saving}
							style={{ padding: "12px 18px" }}
						>
							{t("registers.saveAdd")}
						</Btn>

						{/*
							The way out, once anything has been banked.

							"Save and add another" clears the form for the next one, and both
							save buttons need a complete form — so an operator who added two
							registers and then changed their mind about a third was left with
							no enabled control at all, and no way to reach the review. This
							does not depend on the form: it is about what has already been
							saved, which is exactly what it counts.
						*/}
						{!editing && saved > 0 && !form.complete && (
							<Btn
								variant="secondary"
								onClick={() => navigate(paths.review)}
								style={{ padding: "12px 18px" }}
							>
								{t("registers.doneAdding", { count: saved })}
							</Btn>
						)}

						<div className="grow" />
						<button type="button" onClick={startNew} className="linkbutton" style={{ color: "var(--muted-2)", fontSize: 13 }}>
							{t("common.discard")}
						</button>
					</div>
				</div>
			</div>
		</Page>
	);
}

/* ── Shared pieces ──────────────────────────────────────────────────────── */

function allTouched(): Record<string, boolean> {
	return Object.fromEntries(Object.keys(BLANK).map((k) => [k, true]));
}

function LockedNotice() {
	return (
		<div
			className="row"
			style={{
				gap: 10,
				padding: "14px 16px",
				background: "var(--surface-2)",
				border: "1px dashed var(--line-field)",
				borderRadius: 8,
				fontSize: 12.5,
				color: "var(--muted)",
			}}
		>
			<Mark kind="idle" size={15}>
				{null}
			</Mark>
			<span>
				<T k="registers.locked" params={{ count: CRN_LENGTH }} />
			</span>
		</div>
	);
}

/** Resolve a field's message: the server's objection wins over the local one. */
function useFieldError(form: FormApi, error: unknown) {
	const text = useProblemText();
	const server = serverFieldErrors(error);
	return (key: keyof Values) =>
		text(server[key] ?? (form.touched[key] ? form.problems[key] : null) ?? undefined);
}

function IdentityFields({
	form,
	error,
	gap,
	unusedHint = false,
}: {
	form: FormApi;
	error: unknown;
	gap: number;
	unusedHint?: boolean;
}) {
	const t = useT();
	const err = useFieldError(form, error);

	return (
		<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap }}>
			<TextField
				label={t("registers.crn.label")}
				value={form.values.crn}
				onChange={form.set("crn")}
				onBlur={form.touch("crn")}
				numeric
				mono
				maxLength={CRN_LENGTH}
				placeholder={t("registers.crn.placeholder", { count: CRN_LENGTH })}
				error={err("crn")}
				valid={!form.problems.crn}
				validHint={
					unusedHint ? t("registers.crn.unused") : t("registers.crn.valid", { count: CRN_LENGTH })
				}
			/>
			<TextField
				label={t("registers.name.label")}
				value={form.values.registerName}
				onChange={form.set("registerName")}
				onBlur={form.touch("registerName")}
				placeholder={t("registers.name.placeholder")}
				error={err("registerName")}
				valid={!form.problems.registerName}
				hint={t("registers.name.hint")}
			/>
		</div>
	);
}

function AddressFields({
	form,
	error,
	heading,
	compact = false,
}: {
	form: FormApi;
	error: unknown;
	heading?: ReactNode;
	compact?: boolean;
}) {
	const t = useT();
	const { data: cities = [] } = useCities();
	const err = useFieldError(form, error);

	const grid = (
		<div
			style={{
				display: "grid",
				gridTemplateColumns: "1fr 1fr",
				gap: compact ? "16px 20px" : "14px 22px",
			}}
		>
			<TextField
				label={t("registers.field.building")}
				value={form.values.buildingNumber}
				onChange={form.set("buildingNumber")}
				onBlur={form.touch("buildingNumber")}
				numeric
				mono
				maxLength={4}
				placeholder="8734"
				error={err("buildingNumber")}
			/>
			<TextField
				label={t("registers.field.street")}
				value={form.values.street}
				onChange={form.set("street")}
				onBlur={form.touch("street")}
				error={err("street")}
			/>
			<TextField
				label={t("registers.field.district")}
				value={form.values.district}
				onChange={form.set("district")}
				onBlur={form.touch("district")}
				error={err("district")}
			/>
			<ComboField
				label={t("registers.field.city")}
				value={form.values.city}
				onChange={form.set("city")}
				onBlur={form.touch("city")}
				options={cities.map((c) => c.name)}
				placeholder={t("registers.city.placeholder")}
				error={err("city")}
			/>
			<TextField
				label={t("registers.field.postal")}
				value={form.values.postalCode}
				onChange={form.set("postalCode")}
				onBlur={form.touch("postalCode")}
				numeric
				mono
				maxLength={5}
				placeholder="12211"
				error={err("postalCode")}
			/>
			{compact ? (
				<TextField
					label={t("registers.field.additional")}
					value={form.values.additionalNumber}
					onChange={form.set("additionalNumber")}
					onBlur={form.touch("additionalNumber")}
					numeric
					mono
					maxLength={4}
					placeholder={t("common.optionalValue")}
					error={err("additionalNumber")}
				/>
			) : (
				<TextField
					label={t("registers.field.country")}
					value="Saudi Arabia"
					onChange={() => {}}
					locked
					trailing={<span className="field__lock">{t("common.locked")}</span>}
				/>
			)}
		</div>
	);

	if (compact) return grid;

	return (
		<div className="col" style={{ gap: 14 }}>
			{heading}
			{grid}
			<div style={{ fontSize: 11.5, color: "var(--muted-2)" }}>
				<T k="registers.address.note" />
			</div>
		</div>
	);
}

function BankedRow({
	register,
	phase,
	open,
	editing,
	onToggle,
	onEdit,
	onRemove,
	removing,
}: {
	register: Register;
	phase: Setup["phase"];
	open: boolean;
	editing: boolean;
	onToggle: () => void;
	onEdit: () => void;
	onRemove: () => void;
	removing: boolean;
}) {
	const t = useT();
	const { address } = register;
	const live = register.status === "live";

	return (
		<div
			style={{
				borderBottom: "1px solid var(--line-hair)",
				background: open || editing ? "var(--surface-2)" : undefined,
			}}
		>
			<button
				type="button"
				onClick={onToggle}
				aria-expanded={open}
				className="row"
				style={{
					width: "100%",
					padding: "14px 18px",
					gap: 11,
					border: "none",
					background: "none",
					cursor: "pointer",
					textAlign: "start",
				}}
			>
				<Mark kind="tick" size={18} font={10} />
				<div className="col" style={{ flex: 1, gap: 2 }}>
					<div style={{ fontSize: 13, fontWeight: 600 }}>{register.registerName}</div>
					<div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
						{register.crn}
					</div>
				</div>
				<div style={{ fontSize: 11, color: open ? "var(--brand)" : "var(--muted-2)" }}>
					{open ? "▴" : "▾"}
				</div>
			</button>

			{open && (
				<div className="col" style={{ padding: "0 18px 16px 47px", gap: 9 }}>
					<SummaryRow
						k={t("registers.summary.address")}
						v={`${address.buildingNumber} ${address.street}, ${address.district}, ${address.city} ${address.postalCode}`}
					/>
					<SummaryRow k={t("registers.summary.building")} v={address.buildingNumber} mono />
					<SummaryRow
						k={t("registers.summary.mode")}
						v={phase ? t(PHASE_KEY[phase]) : "—"}
					/>
					<div style={{ display: "flex", gap: 14, marginTop: 2 }}>
						<button
							type="button"
							onClick={onEdit}
							disabled={live}
							title={live ? t("api.liveNoEdit") : undefined}
							className="linkbutton"
							style={{ fontSize: 12, fontWeight: 600 }}
						>
							{t("common.edit")}
						</button>
						<button
							type="button"
							onClick={onRemove}
							disabled={removing || live}
							title={live ? t("api.liveNoRemove") : undefined}
							className="linkbutton"
							style={{ fontSize: 12, fontWeight: 600, color: "var(--danger)" }}
						>
							{t("common.remove")}
						</button>
					</div>
				</div>
			)}
		</div>
	);
}

function SummaryRow({ k, v, mono = false }: { k: string; v: string; mono?: boolean }) {
	return (
		<div style={{ display: "flex", gap: 10 }}>
			<div style={{ width: 88, flex: "none", fontSize: 11.5, color: "var(--muted-2)" }}>{k}</div>
			<div className={mono ? "mono" : undefined} style={{ fontSize: 12, lineHeight: 1.45 }}>
				{v}
			</div>
		</div>
	);
}
