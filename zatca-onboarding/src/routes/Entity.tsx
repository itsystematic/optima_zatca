import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Problem } from "@/api";
import { Page } from "@/components/Page";
import { SelectField, TextField } from "@/components/inputs";
import { Btn, Eyebrow, Rule } from "@/components/primitives";
import { Stepper } from "@/components/Stepper";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { FormError } from "@/components/FormError";
import { useProblemText, serverFieldErrors } from "@/lib/errors";
import { formatDate, relativeTime } from "@/lib/format";
import { TIN_LENGTH, hasArabicScript, isValidTin, legalNameArProblem, tinProblem } from "@/lib/validation";
import {
	useCompanies,
	useGuidance,
	useMarkEntityVerified,
	useSaveEntity,
	useSetup,
} from "@/queries/setup";
import { paths } from "./paths";

const VERIFY_STEPS: MessageKey[] = ["entity.verify.s1", "entity.verify.s2", "entity.verify.s3"];

/** 05 — three fields, the helper panel pinned, and nothing accepted until it matches. */
export function Entity() {
	const navigate = useNavigate();
	const t = useT();
	const text = useProblemText();
	const { data: setup } = useSetup();
	const { data: companies = [] } = useCompanies();
	const { data: guidance } = useGuidance();
	const saveEntity = useSaveEntity();
	const markVerified = useMarkEntityVerified();

	const [company] = useState(setup?.entity?.company ?? setup?.company ?? "");
	const [legalNameAr, setLegalNameAr] = useState(setup?.entity?.legalNameAr ?? "");
	const [tin, setTin] = useState(setup?.entity?.tin ?? "");
	// errors only appear once a field has been visited, so a fresh form is calm
	const [touched, setTouched] = useState<Record<string, boolean>>({});

	/**
	 * The company arrives pre-selected from the setup record, so its stored
	 * defaults should be offered on first paint too — not only when the operator
	 * opens the picker. Runs once, and never over anything already entered.
	 */
	const seeded = useRef(false);
	useEffect(() => {
		if (seeded.current || setup?.entity || !companies.length || !company) return;
		const match = companies.find((c) => c.name === company);
		if (!match) return;
		seeded.current = true;
		const filled: Record<string, boolean> = {};
		if (!legalNameAr && match.defaultLegalNameAr) {
			setLegalNameAr(match.defaultLegalNameAr);
			filled.legalNameAr = true;
		}
		if (!tin && match.defaultTin) {
			setTin(match.defaultTin);
			filled.tin = true;
		}
		if (Object.keys(filled).length) setTouched((prev) => ({ ...prev, ...filled }));
	}, [companies, company, setup?.entity, legalNameAr, tin]);

	const serverErrors = serverFieldErrors(saveEntity.error);

	const problems = useMemo(
		() => ({
			company: company ? null : ({ key: "validation.company.required" } as Problem),
			legalNameAr: legalNameArProblem(legalNameAr),
			tin: tinProblem(tin),
		}),
		[company, legalNameAr, tin],
	);

	const shown = (field: keyof typeof problems) =>
		text(serverErrors[field] ?? (touched[field] ? problems[field] : null) ?? undefined);

	const openCount = Object.values(problems).filter(Boolean).length;
	const complete = openCount === 0;
	const chosen = companies.find((c) => c.name === company);

	/**
	 * The company is not chosen here.
	 *
	 * A setup belongs to a company, and every answer already given is stored
	 * against it. Changing it on this screen used to open that company's own
	 * record — a different one, with its own decisions — so the obligation and
	 * scope just answered were abandoned and the wizard bounced back to its first
	 * step. It is settled before the wizard starts instead, and shown here as
	 * fact. The server refuses a mismatch outright, so this is not merely a
	 * disabled control.
	 */

	const submit = () => {
		setTouched({ company: true, legalNameAr: true, tin: true });
		if (!complete || !setup) return;
		// always write to the setup on screen, never to whatever the select shows
		saveEntity.mutate(
			{ company: setup.company, legalNameAr: legalNameAr.trim(), tin },
			{ onSuccess: () => navigate(paths.registers) },
		);
	};

	return (
		<Page guide="entity"
			width={1040}
			status={setup ? t("entity.saved", { when: relativeTime(setup.modified) }) : undefined}
		>
			<div className="col" style={{ gap: 24 }}>
				<Stepper
					size="lg"
					steps={[
						{ badge: "1", label: t("steps.entity"), sub: t("steps.inProgress"), state: "current" },
						{ badge: "2", label: t("steps.registers"), sub: t("steps.next"), state: "idle" },
						{ badge: "3", label: t("steps.review"), state: "idle" },
						{ badge: "4", label: t("steps.register"), state: "idle" },
					]}
				/>

				<div
					style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24, alignItems: "start" }}
				>
					<form
						className="card col"
						style={{ padding: 32, gap: 26 }}
						onSubmit={(e) => {
							e.preventDefault();
							submit();
						}}
					>
						<div className="col" style={{ gap: 7 }}>
							<h2 className="title" style={{ fontSize: 21, letterSpacing: "-.015em" }}>
								{t("entity.title")}
							</h2>
							<div style={{ fontSize: 13.5, color: "var(--muted)" }}>{t("entity.body")}</div>
						</div>

						<FormError error={saveEntity.error} />

						<SelectField
							label={t("entity.company.label")}
							value={company}
							onChange={() => {}}
							options={[company]}
							placeholder={t("entity.company.placeholder")}
							valid={Boolean(company)}
							locked
							hint={t(
								chosen && !chosen.linked
									? "entity.company.unlinked"
									: companies.length > 1
										? "entity.company.locked"
										: "entity.company.linked",
							)}
						/>

						<TextField
							label={t("entity.arabic.label")}
							labelMeta={t("common.required")}
							labelMetaTone="req"
							value={legalNameAr}
							onChange={setLegalNameAr}
							onBlur={() => setTouched((prev) => ({ ...prev, legalNameAr: true }))}
							arabic
							dir="rtl"
							placeholder={t("entity.arabic.placeholder")}
							error={shown("legalNameAr")}
							valid={!problems.legalNameAr}
							validHint={hasArabicScript(legalNameAr) ? t("entity.arabic.valid") : undefined}
							hint={t("entity.arabic.hint")}
						/>

						<TextField
							label={t("entity.tin.label")}
							labelMeta={t("entity.tin.meta", { count: TIN_LENGTH })}
							labelMetaTone="mono"
							value={tin}
							onChange={setTin}
							onBlur={() => setTouched((prev) => ({ ...prev, tin: true }))}
							numeric
							mono
							maxLength={TIN_LENGTH + 2}
							placeholder={t("entity.tin.placeholder")}
							error={shown("tin")}
							valid={isValidTin(tin)}
							validHint={t("entity.tin.valid")}
							counter={isValidTin(tin) ? undefined : `${tin.length} / ${TIN_LENGTH}`}
						/>

						<Rule />
						<div className="actions">
							<Btn type="submit" disabled={!complete} busy={saveEntity.isPending}>
								{t("common.continue")}
							</Btn>
							<Btn variant="secondary" onClick={() => navigate(paths.scope)}>
								{t("common.back")}
							</Btn>
							<div style={{ fontSize: 12, color: "var(--muted-2)" }}>
								{complete ? t("entity.ready") : t("entity.fix", { count: openCount })}
							</div>
						</div>
					</form>

					<aside className="card col" style={{ padding: 24, gap: 16, position: "sticky", top: 0 }}>
						<div className="row" style={{ gap: 10 }}>
							<div
								style={{
									width: 26,
									height: 26,
									borderRadius: 6,
									background: "var(--brand-tint)",
									border: "1px solid var(--brand-line)",
								}}
							/>
							<Eyebrow tone="brand">{t("entity.verify.title")}</Eyebrow>
						</div>
						<div
							className="pretty"
							style={{ fontSize: 13.5, lineHeight: 1.55, color: "var(--ink-2)" }}
						>
							{t("entity.verify.body")}
						</div>
						<div
							className="col"
							style={{
								gap: 11,
								padding: 16,
								background: "var(--surface-2)",
								border: "1px solid var(--line-hair)",
								borderRadius: 8,
							}}
						>
							{VERIFY_STEPS.map((key, i) => (
								<div key={key} style={{ display: "flex", gap: 10 }}>
									<div
										className="mono"
										style={{ fontSize: 11.5, color: "var(--brand)", fontWeight: 600 }}
									>
										0{i + 1}
									</div>
									<div style={{ fontSize: 12.5, lineHeight: 1.5 }}>
										<T k={key} />
									</div>
								</div>
							))}
						</div>
						<a
							href={guidance?.portalUrl}
							target="_blank"
							rel="noreferrer"
							style={{ fontSize: 13, fontWeight: 600 }}
						>
							{t("entity.verify.link")}
						</a>
						<Rule />
						{setup?.entityVerifiedOn ? (
							<div style={{ fontSize: 11.5, lineHeight: 1.5, color: "var(--ok)" }}>
								{t("entity.verify.on", { date: formatDate(setup.entityVerifiedOn) })}
							</div>
						) : (
							<div className="col" style={{ gap: 10 }}>
								<div style={{ fontSize: 11.5, lineHeight: 1.5, color: "var(--muted-2)" }}>
									{t("entity.verify.never")}
								</div>
								<Btn
									size="sm"
									variant="secondary"
									busy={markVerified.isPending}
									onClick={() => markVerified.mutate(undefined as never)}
								>
									{t("entity.verify.action")}
								</Btn>
							</div>
						)}
					</aside>
				</div>
			</div>
		</Page>
	);
}
