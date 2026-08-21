import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Scope as ScopeValue } from "@/api";
import { Page } from "@/components/Page";
import { ChoiceCard, TextField } from "@/components/inputs";
import { FormError } from "@/components/FormError";
import { Btn, Eyebrow, Radio } from "@/components/primitives";
import { useT } from "@/i18n/core";
import { T } from "@/i18n/core";
import { useSaveScope, useSetup } from "@/queries/setup";
import { paths } from "./paths";

/** 04 — each option previews the work it creates downstream. */
export function Scope() {
	const navigate = useNavigate();
	const t = useT();
	const { data: setup } = useSetup();
	const saveScope = useSaveScope();

	const [choice, setChoice] = useState<ScopeValue>(setup?.scope ?? "multiple");
	const [expected, setExpected] = useState(
		setup?.expectedRegisters && setup.scope === "multiple" ? String(setup.expectedRegisters) : "",
	);

	const expectedCount = Number(expected);
	const expectedProblem =
		choice === "multiple" && expected && (expectedCount < 2 || expectedCount > 99)
			? t("scope.expected.range")
			: null;

	const submit = () =>
		saveScope.mutate(
			{
				scope: choice,
				expectedRegisters: choice === "multiple" && expectedCount >= 2 ? expectedCount : undefined,
			},
			{ onSuccess: () => navigate(paths.entity) },
		);

	return (
		<Page guide="scope" width={1040} pad="44px 40px">
			<div className="col" style={{ gap: 30 }}>
				<div className="col" style={{ gap: 8 }}>
					<Eyebrow size="lg">{t("scope.eyebrow")}</Eyebrow>
					<h2 className="title" style={{ fontSize: 28, letterSpacing: "-.02em" }}>
						{t("scope.title")}
					</h2>
					<p style={{ margin: 0, fontSize: 14, color: "var(--muted)" }}>{t("scope.body")}</p>
				</div>

				<FormError error={saveScope.error} />

				<div
					style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}
					role="radiogroup"
					aria-label={t("scope.title")}
				>
					<ChoiceCard
						selected={choice === "single"}
						onSelect={() => setChoice("single")}
						style={{ padding: 28, gap: 20 }}
					>
						<ScopeHead
							selected={choice === "single"}
							title={t("scope.single.title")}
							tag={t("scope.single.tag")}
						/>
						<div
							className="row"
							style={{
								gap: 8,
								padding: 18,
								background: "var(--surface-2)",
								border: "1px solid var(--line-hair)",
								borderRadius: 8,
							}}
						>
							<div
								style={{
									width: 64,
									height: 44,
									borderRadius: 6,
									border: "1.5px solid var(--line-control)",
									background: "var(--surface)",
								}}
							/>
							<div className="mono" style={{ fontSize: 11.5, color: "var(--muted-2)" }}>
								{t("scope.single.preview")}
							</div>
						</div>
						<div className="col" style={{ gap: 10 }}>
							<Eyebrow>{t("scope.downstream")}</Eyebrow>
							<div style={{ fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-2)" }}>
								{t("scope.single.body")}
							</div>
						</div>
					</ChoiceCard>

					<ChoiceCard
						selected={choice === "multiple"}
						onSelect={() => setChoice("multiple")}
						style={{ padding: 28, gap: 20 }}
					>
						<ScopeHead
							selected={choice === "multiple"}
							title={t("scope.multiple.title")}
							tag={t("scope.multiple.tag")}
						/>
						<div
							className="row"
							style={{
								gap: 8,
								padding: 18,
								background: "var(--brand-tint-3)",
								border: "1px solid var(--brand-line-2)",
								borderRadius: 8,
							}}
						>
							<div style={{ display: "flex", gap: 6 }}>
								{[
									"1.5px solid var(--brand)",
									"1.5px solid var(--brand)",
									"1.5px solid var(--brand-line-3)",
									"1.5px dashed var(--brand-line-3)",
								].map((border, i) => (
									<div
										key={i}
										style={{
											width: 34,
											height: 44,
											borderRadius: 5,
											border,
											background: "var(--surface)",
										}}
									/>
								))}
							</div>
							<div className="mono" style={{ fontSize: 11.5, color: "var(--brand)" }}>
								{expectedCount >= 2
									? t("scope.multiple.preview", { count: expectedCount })
									: t("scope.multiple.previewUnknown")}
							</div>
						</div>
						<div className="col" style={{ gap: 10 }}>
							<Eyebrow tone="brand">{t("scope.downstream")}</Eyebrow>
							<div style={{ fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-2)" }}>
								<T k="scope.multiple.body" />
							</div>
						</div>

						{/* revealed only once this option is live, so the other card stays quiet */}
						{choice === "multiple" && (
							<div style={{ maxWidth: 220 }} onClick={(e) => e.stopPropagation()}>
								<TextField
									label={t("scope.expected.label")}
									labelMeta={t("common.optional")}
									value={expected}
									onChange={setExpected}
									numeric
									maxLength={2}
									mono
									placeholder="5"
									error={expectedProblem}
									hint={t("scope.expected.hint")}
								/>
							</div>
						)}
					</ChoiceCard>
				</div>

				<div className="actions">
					<Btn onClick={submit} busy={saveScope.isPending} disabled={Boolean(expectedProblem)}>
						{t("common.continue")}
					</Btn>
					<Btn variant="secondary" onClick={() => navigate(paths.mode)}>
						{t("common.back")}
					</Btn>
				</div>
			</div>
		</Page>
	);
}

function ScopeHead({
	title,
	tag,
	selected,
}: {
	title: string;
	tag: string;
	selected: boolean;
}) {
	return (
		<div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
			<Radio on={selected} />
			<div className="col" style={{ gap: 5 }}>
				<div style={{ fontSize: 19, fontWeight: 600 }}>{title}</div>
				<div style={{ fontSize: 13, color: "var(--muted)" }}>{tag}</div>
			</div>
		</div>
	);
}
