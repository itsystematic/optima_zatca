import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Finding, Phase, PhaseOption } from "@/api";
import { Page } from "@/components/Page";
import { ChoiceCard } from "@/components/inputs";
import { FormError } from "@/components/FormError";
import { Btn, Chip, Eyebrow, Mark, Radio, Rule } from "@/components/primitives";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { usePhaseOptions, useSaveMode, useSetup } from "@/queries/setup";
import { paths } from "./paths";

type ModeCopy = { phase: Phase; unlocks: MessageKey[] };

/** Which bullets each obligation shows; the copy itself lives in the catalogue. */
const MODES: ModeCopy[] = [
	{ phase: "phase_1", unlocks: ["mode.phase1.u1", "mode.phase1.u2", "mode.phase1.u3"] },
	{
		phase: "phase_2",
		unlocks: ["mode.phase2.u1", "mode.phase2.u2", "mode.phase2.u3", "mode.phase2.u4"],
	},
];

const SLUG: Record<Phase, "phase1" | "phase2"> = { phase_1: "phase1", phase_2: "phase2" };

/**
 * Nothing is recommended here.
 *
 * The server decides, and only when it has a fact that justifies it — which it
 * returns alongside, so the card can say what that fact was. This screen
 * previously carried a hardcoded recommendation and told the operator their "VAT
 * registration is above the Phase 2 threshold", which nothing had checked and
 * which no accounting system can check: the authority assigns the wave and tells
 * the taxpayer directly.
 */
const FALLBACK: Phase = "phase_2";

/** 03 — cards sell capability, not phase numbers, and the pick is justified. */
export function Mode() {
	const navigate = useNavigate();
	const t = useT();
	const { data: setup } = useSetup();
	const { data: options } = usePhaseOptions();
	const saveMode = useSaveMode();

	const optionFor = (phase: Phase): PhaseOption | undefined =>
		options?.find((o) => o.phase === phase);
	const recommended = options?.find((o) => o.recommended)?.phase;

	// whatever is already saved, then whatever the server recommends, then the
	// obligation most companies are under — but never one that is blocked
	const [choice, setChoice] = useState<Phase>(setup?.phase ?? FALLBACK);
	const eligible = (phase: Phase) => optionFor(phase)?.eligible ?? true;

	/**
	 * What would actually be saved, or nothing.
	 *
	 * Falling back to the operator's last pick when no obligation is available
	 * left a blocked card reading as chosen and the continue button live, which
	 * promised a step that could only fail. When nothing can be chosen there is
	 * no selection to show and nowhere to continue to.
	 */
	const selectable: Phase | null = eligible(choice)
		? choice
		: (options?.find((o) => o.eligible)?.phase ?? null);

	const submit = () => {
		if (!selectable) return;
		saveMode.mutate({ phase: selectable }, { onSuccess: () => navigate(paths.scope) });
	};

	return (
		<Page guide="mode" width={1040} pad="36px 40px 44px">
			<div className="col" style={{ gap: 28 }}>
				<div className="col" style={{ gap: 8 }}>
					<Eyebrow size="lg">{t("mode.eyebrow")}</Eyebrow>
					<h2 className="title" style={{ fontSize: 28, letterSpacing: "-.02em" }}>
						{t("mode.title")}
					</h2>
					<p style={{ margin: 0, fontSize: 14, color: "var(--muted)" }}>{t("mode.body")}</p>
				</div>

				<FormError error={saveMode.error} />

				<div
					className="stagger"
					style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}
					role="radiogroup"
					aria-label={t("mode.title")}
				>
					{MODES.map((m) => {
						const option = optionFor(m.phase);
						const blocked = option ? !option.eligible : false;
						const selected = !blocked && selectable === m.phase;
						const slug = SLUG[m.phase];
						return (
							<ChoiceCard
								key={m.phase}
								selected={selected}
								disabled={blocked}
								onSelect={() => setChoice(m.phase)}
								style={{ padding: 28, gap: 18 }}
							>
								{blocked ? (
									<Chip tone="outline">{t("mode.unavailable")}</Chip>
								) : (
									recommended === m.phase && <Chip tone="ribbon">{t("mode.recommended")}</Chip>
								)}
								<div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
									<Radio on={selected} />
									<div className="col" style={{ gap: 5 }}>
										<div style={{ fontSize: 19, fontWeight: 600 }}>
											{t(`mode.${slug}.title` as MessageKey)}
										</div>
										<div style={{ fontSize: 13, color: "var(--muted)" }}>
											{t(`mode.${slug}.tag` as MessageKey)}
										</div>
									</div>
								</div>
								<Rule />
								<div className="col" style={{ gap: 12 }}>
									<Eyebrow tone={selected ? "brand" : "muted"}>{t("mode.unlocks")}</Eyebrow>
									{m.unlocks.map((key) => (
										<div key={key} style={{ display: "flex", gap: 10 }}>
											<Mark kind={selected ? "brand" : "idle"} size={15} style={{ marginTop: 2 }}>
												{null}
											</Mark>
											<div style={{ fontSize: 13.5, lineHeight: 1.5 }}>
												<T k={key} />
											</div>
										</div>
									))}
								</div>
								<div
									className="col"
									style={{
										marginTop: "auto",
										paddingTop: 14,
										borderTop: "1px solid var(--line-hair)",
										gap: 6,
									}}
								>
									<Findings
										blockers={option?.blockers ?? []}
										notes={option?.notes ?? []}
										because={
											recommended === m.phase ? (option?.recommendedBecause ?? null) : null
										}
									/>
									<div style={{ fontSize: 12.5, color: "var(--muted)" }}>
										<T k={`mode.${slug}.foot` as MessageKey} />
									</div>
									<div
										className="mono"
										style={{ fontSize: 11, color: selected ? "var(--brand)" : "var(--muted-2)" }}
									>
										{t(`mode.${slug}.mono` as MessageKey)}
									</div>
								</div>
							</ChoiceCard>
						);
					})}
				</div>

				<div className="actions" style={{ marginTop: "auto" }}>
					<Btn onClick={submit} disabled={!selectable} busy={saveMode.isPending}>
						{t("common.continue")}
					</Btn>
					<div
						style={{
							fontSize: 12.5,
							color: selectable ? "var(--muted-2)" : "var(--danger)",
						}}
					>
						{selectable
							? t("mode.selected", {
									mode: t(`mode.${SLUG[selectable]}.title` as MessageKey),
								})
							: t("mode.noneAvailable")}
					</div>
				</div>
			</div>
		</Page>
	);
}

/**
 * What the server found, and what it could not.
 *
 * Three registers of certainty, kept visibly apart: a blocker is a fact that
 * stops this choice, a note is a condition the operator has to confirm because
 * nothing here can, and the reason for a recommendation is the fact that earned
 * it. Collapsing them into one list would let an unverified claim borrow the
 * authority of a checked one, which is how this screen came to assert a revenue
 * threshold nobody had measured.
 */
function Findings({
	blockers,
	notes,
	because,
}: {
	blockers: Finding[];
	notes: Finding[];
	because: string | null;
}) {
	const t = useT();
	if (!blockers.length && !notes.length && !because) return null;

	return (
		<div className="col" style={{ gap: 6, marginBottom: 4 }}>
			{blockers.map((f) => (
				<div key={f.key} style={{ fontSize: 12.5, color: "var(--danger)", lineHeight: 1.45 }}>
					{t(f.key as MessageKey, f.params)}
				</div>
			))}
			{notes.map((f) => (
				<div key={f.key} style={{ fontSize: 12.5, color: "var(--warn)", lineHeight: 1.45 }}>
					{t(f.key as MessageKey, f.params)}
				</div>
			))}
			{because && (
				<div style={{ fontSize: 12.5, color: "var(--brand)", lineHeight: 1.45 }}>
					{t(because as MessageKey)}
				</div>
			)}
		</div>
	);
}
