import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Confetti } from "@/components/Confetti";
import { Page } from "@/components/Page";
import { Btn, Chip, Eyebrow, Mark, Rule } from "@/components/primitives";
import { isLive } from "@/components/Environment";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { formatDate, formatDateTime } from "@/lib/format";
import { useCompanies, useSetup, useSwitchCompany } from "@/queries/setup";
import { openDesk, supportWhatsApp } from "@/lib/desk";
import { paths } from "./paths";

const ACTIVE: Record<"phase_1" | "phase_2", MessageKey[]> = {
	phase_2: ["done.active.p2a", "done.active.p2b", "done.active.p2c"],
	phase_1: ["done.active.p1a", "done.active.p1b", "done.active.p1c"],
};

/** 12 — states what is legally active now, then routes to the first real task. */
export function Done() {
	const navigate = useNavigate();
	const t = useT();
	const { data: setup } = useSetup();
	const { data: companies } = useCompanies();
	const switchCompany = useSwitchCompany();
	if (!setup) return null;

	/**
	 * Phase one obtains no certificates and queues no jobs: it puts a QR code on
	 * the printed invoice and transmits nothing. There is therefore no run to
	 * open and nothing that could be outstanding, so the finish card — whose only
	 * control navigates to the progress board — has nothing to offer and is not
	 * shown. Left in, its button went to a board with no run on it.
	 */
	const hasRun = setup.phase !== "phase_1";

	const live = setup.registers.filter((r) => r.status === "live");
	const outstanding = hasRun ? setup.registers.filter((r) => r.status !== "live") : [];
	const certificate = live[0]?.certificate ?? null;
	const active = ACTIVE[setup.phase === "phase_1" ? "phase_1" : "phase_2"];

	// A setup belongs to one company, so finishing one says nothing about the
	// rest. Nothing else on this screen leads back out of it, and the chosen
	// company is held for the tab — without this the other companies on a site
	// are unreachable once the first one is done.
	const others = (companies ?? []).filter((c) => c.name !== setup.company);
	const unregistered = others.filter((c) => c.status === "not_started");

	// Only a clean finish: nothing outstanding. Celebrating a run that half failed
	// would be telling the operator the opposite of what the screen below it says.
	//
	// Counted from the registers rather than from `live`, because a completed
	// phase one has registers but no certificates — and testing for a live
	// certificate withheld the confetti from the one obligation that finishes in
	// a single step.
	const clean =
		Boolean(setup.completedAt) && setup.registers.length > 0 && outstanding.length === 0;

	return (
		<Page
			guide="done"
			width={1040}
			pad="24px 40px 40px"
			status={
				// the "Live" badge means the registration finished, which is not the
				// same as the invoices counting; it only claims that on production
				isLive(setup.environment) ? (
					<Chip tone="ok" pill>
						{t("common.live")}
					</Chip>
				) : null
			}
		>
			<Confetti run={clean} />

			<div className="col" style={{ gap: 22 }}>
				<div className="card" style={{ padding: "40px 44px", display: "flex", gap: 32 }}>
					<div
						style={{
							width: 56,
							height: 56,
							flex: "none",
							borderRadius: 14,
							background: "var(--ok-tint)",
							border: "1px solid var(--ok-line)",
							color: "var(--ok)",
							fontSize: 26,
							fontWeight: 700,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						✓
					</div>
					<div className="col" style={{ gap: 12, flex: 1 }}>
						<h2
							className="title"
							style={{ fontSize: 32, letterSpacing: "-.022em", lineHeight: 1.15 }}
						>
							{t("done.title", { company: setup.company })}
						</h2>
						<p
							className="pretty"
							style={{
								margin: 0,
								fontSize: 15,
								lineHeight: 1.6,
								color: "var(--ink-2)",
								maxWidth: 680,
							}}
						>
							{/*
							 * Phase one obtains no certificate and clears nothing, so the
							 * sentence about cryptographic stamping and automatic clearance
							 * is not true of it. It described the phase two outcome to
							 * everybody, including the people who had just chosen the
							 * obligation that does neither.
							 */}
							{t(hasRun ? "done.body" : "done.body.phase1", { count: live.length })}
							{outstanding.length > 0 && <> {t("done.outstanding", { count: outstanding.length })}</>}
						</p>
						<div className="mono" style={{ fontSize: 11.5, color: "var(--muted-2)", marginTop: 2 }}>
							{t("done.reference", { ref: setup.reference ?? "—" })}
							{setup.completedAt &&
								` · ${t("done.completed", { when: formatDateTime(setup.completedAt) })}`}
						</div>
					</div>
				</div>

				<div
					style={{ display: "grid", gridTemplateColumns: "1.15fr 1fr", gap: 20, alignItems: "start" }}
				>
					<div className="card col" style={{ padding: "24px 26px", gap: 16 }}>
						<Eyebrow>{t("done.active")}</Eyebrow>
						<div className="col" style={{ gap: 13 }}>
							{active.map((key) => (
								<div key={key} style={{ display: "flex", gap: 11 }}>
									<Mark kind="tick" size={17} font={10} style={{ marginTop: 2 }} />
									<div style={{ fontSize: 13.5, lineHeight: 1.5 }}>
										<T k={key} />
									</div>
								</div>
							))}
						</div>
						<Rule />
						<div className="col" style={{ gap: 8 }}>
							<Fact k={t("done.fact.certificates")}>
								{!hasRun
									? t("done.certNone")
									: certificate?.validTo
										? t("done.certValue", {
												count: live.length,
												date: formatDate(certificate.validTo),
											})
										: t("done.certCount", { count: live.length })}
							</Fact>
							<Fact k={t("done.fact.fingerprint")} mono>
								{certificate?.fingerprint ?? "—"}
							</Fact>
							<Fact k={t("done.fact.renewal")}>
								{t(hasRun ? "done.renewalValue" : "done.renewalNone")}
							</Fact>
						</div>
					</div>

					<div className="col" style={{ gap: 14 }}>
						<Eyebrow style={{ paddingTop: 4 }}>{t("done.next")}</Eyebrow>

						{outstanding.length > 0 ? (
							<div
								className="card card--selected col"
								style={{ padding: "20px 22px", gap: 8, boxShadow: "var(--shadow-brand-sm)" }}
							>
								<div style={{ fontSize: 16, fontWeight: 600 }}>
									{t("done.finish.title", { count: outstanding.length })}
								</div>
								<div style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--muted)" }}>
									{t("done.finish.body")}
								</div>
								<div style={{ marginTop: 6 }}>
									<Btn size="sm" onClick={() => navigate(paths.progress)}>
										{t("done.finish.cta")}
									</Btn>
								</div>
							</div>
						) : (
							<div
								className="card card--selected col"
								style={{ padding: "20px 22px", gap: 8, boxShadow: "var(--shadow-brand-sm)" }}
							>
								{/* phase one adds a QR code on submit; it clears nothing */}
								<div style={{ fontSize: 16, fontWeight: 600 }}>
									{t(hasRun ? "done.invoice.title" : "done.invoice.title.phase1")}
								</div>
								<div style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--muted)" }}>
									{t(hasRun ? "done.invoice.body" : "done.invoice.body.phase1")}
								</div>
								<div style={{ marginTop: 6 }}>
									{/* the desk, not this app — see lib/desk */}
									<Btn size="sm" onClick={() => openDesk("Sales Invoice", "new")}>
										{t("done.invoice.cta")}
									</Btn>
								</div>
							</div>
						)}

						<div className="card col" style={{ padding: "20px 22px", gap: 6 }}>
							<div style={{ fontSize: 15, fontWeight: 600 }}>{t("done.log.title")}</div>
							<div style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--muted)" }}>
								{t("done.log.body")}
							</div>
							<button
								type="button"
								onClick={() => navigate(paths.log)}
								style={{
									border: "none",
									background: "none",
									padding: 0,
									textAlign: "start",
									cursor: "pointer",
									fontSize: 13,
									fontWeight: 600,
									color: "var(--brand)",
									marginTop: 4,
								}}
							>
								{t("done.log.cta")}
							</button>
						</div>

						{others.length > 0 && (
							<div className="card col" style={{ padding: "20px 22px", gap: 6 }}>
								<div style={{ fontSize: 15, fontWeight: 600 }}>{t("done.another.title")}</div>
								<div style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--muted)" }}>
									{unregistered.length > 0
										? t("done.another.body", { count: unregistered.length })
										: t("done.another.bodyAll")}
								</div>
								<div style={{ marginTop: 8 }}>
									<Btn
										size="sm"
										variant="secondary"
										onClick={() => {
											// drop the scope so the picker opens rather than
											// resuming the company just finished
											switchCompany(null);
											navigate(paths.company);
										}}
									>
										{t("done.another.cta")}
									</Btn>
								</div>
							</div>
						)}

						<div className="card card--quiet row" style={{ padding: "18px 22px", gap: 14 }}>
							<div className="col" style={{ flex: 1, gap: 4 }}>
								<div style={{ fontSize: 13.5, fontWeight: 600 }}>{t("done.support.title")}</div>
								<div style={{ fontSize: 12, color: "var(--muted)" }}>
									{t("done.support.body", { ref: setup.reference ?? "—" })}
								</div>
							</div>
							<Btn
								variant="secondary"
								style={{ padding: "9px 16px", fontSize: 13, fontWeight: 600 }}
								onClick={() =>
									// a new tab, not this one: WhatsApp is somewhere else entirely, and
									// replacing the page would throw away the summary the operator is
									// about to quote from. `noopener` because the opened page is not ours.
									window.open(
										supportWhatsApp({ reference: setup.reference, company: setup.company }),
										"_blank",
										"noopener,noreferrer",
									)
								}
							>
								{t("done.support.cta")}
							</Btn>
						</div>
					</div>
				</div>
			</div>
		</Page>
	);
}

function Fact({ k, children, mono }: { k: string; children: ReactNode; mono?: boolean }) {
	return (
		<div style={{ display: "flex", gap: 10 }}>
			<div style={{ width: 120, flex: "none", fontSize: 11.5, color: "var(--muted-2)" }}>{k}</div>
			<div className={mono ? "mono" : undefined} style={{ fontSize: mono ? 12 : 12.5 }}>
				{children}
			</div>
		</div>
	);
}
