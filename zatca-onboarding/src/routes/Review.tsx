import { useNavigate } from "react-router-dom";
import type { Setup } from "@/api";
import { Page } from "@/components/Page";
import { Btn, Chip, Eyebrow, Mark, Rule } from "@/components/primitives";
import { FormError } from "@/components/FormError";
import { useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { oneLineAddress } from "@/lib/format";
import { useRemoveRegister, useSetAcknowledged, useSetup, useSubmitOtp } from "@/queries/setup";
import { needsOtp, stepPath, paths } from "./paths";

const COLS = "48px 1.5fr 1.1fr .9fr 2fr 1fr 120px";

const PHASE_CHIP: Record<string, MessageKey> = { phase_1: "review.phase1", phase_2: "review.phase2" };

/** 08 — dense table, per-row edit and delete, and a gate on the irreversible step. */
export function Review({ embedded = false }: { embedded?: boolean }) {
	const { data: setup } = useSetup();
	if (!setup) return null;
	return <ReviewBody setup={setup} embedded={embedded} />;
}

function ReviewBody({ setup, embedded }: { setup: Setup; embedded: boolean }) {
	const navigate = useNavigate();
	const t = useT();
	const remove = useRemoveRegister();
	const acknowledge = useSetAcknowledged();
	const submit = useSubmitOtp();

	const count = setup.registers.length;
	// phase 1 issues no certificates, so there is no code to collect: the
	// submission is made from here, with no entries at all
	const collectsOtp = needsOtp(setup);

	const start = () => {
		if (collectsOtp) {
			navigate(paths.otp);
			return;
		}
		submit.mutate(
			{ entries: [] },
			{ onSuccess: (updated) => navigate(stepPath[updated.step]) },
		);
	};

	return (
		<Page guide="review" width={1160}>
			<div className="col" style={{ gap: 22 }}>
				<div style={{ display: "flex", alignItems: "flex-end", gap: 20 }}>
					<div className="col" style={{ gap: 7, flex: 1 }}>
						<Eyebrow size="lg">{t("review.eyebrow")}</Eyebrow>
						<h2 className="title" style={{ fontSize: 26, letterSpacing: "-.02em" }}>
							{t("review.title")}
						</h2>
					</div>
					<div style={{ display: "flex", gap: 26, paddingBottom: 4 }}>
						<Stat n={count} label={t("review.stat.registers", { count })} />
						<Stat n={count} label={t("review.stat.certificates", { count })} />
						{collectsOtp && <Stat n={count} label={t("review.stat.otps", { count })} />}
					</div>
				</div>

				<FormError error={remove.error ?? acknowledge.error ?? submit.error} />

				<div className="card" style={{ overflow: "hidden" }}>
					<div
						className="eyebrow"
						style={{
							display: "grid",
							gridTemplateColumns: COLS,
							background: "var(--surface-2)",
							borderBottom: "1px solid var(--line)",
							letterSpacing: ".11em",
							color: "var(--muted)",
						}}
					>
						<div style={{ padding: "11px 14px" }}>{t("review.col.index")}</div>
						<div style={{ padding: "11px 12px" }}>{t("review.col.name")}</div>
						<div style={{ padding: "11px 12px" }}>{t("review.col.crn")}</div>
						<div style={{ padding: "11px 12px" }}>{t("review.col.city")}</div>
						<div style={{ padding: "11px 12px" }}>{t("review.col.address")}</div>
						<div style={{ padding: "11px 12px" }}>{t("review.col.mode")}</div>
						<div style={{ padding: "11px 14px", textAlign: "end" }}>{t("review.col.actions")}</div>
					</div>

					{setup.registers.map((r) => (
						<div
							key={r.id}
							style={{
								display: "grid",
								gridTemplateColumns: COLS,
								borderBottom: "1px solid var(--line-hair)",
								alignItems: "center",
							}}
						>
							<div className="mono" style={{ padding: 14, fontSize: 12, color: "var(--muted-3)" }}>
								{r.index}
							</div>
							<div style={{ padding: "14px 12px", fontSize: 13.5, fontWeight: 600 }}>
								{r.registerName}
							</div>
							<div className="mono" style={{ padding: "14px 12px", fontSize: 12.5 }}>
								{r.crn}
							</div>
							<div style={{ padding: "14px 12px", fontSize: 13 }}>{r.address.city}</div>
							<div
								style={{
									padding: "14px 12px",
									fontSize: 12.5,
									color: "var(--ink-2)",
									lineHeight: 1.4,
								}}
							>
								{oneLineAddress(r.address)}
							</div>
							<div style={{ padding: "14px 12px" }}>
								<Chip>{setup.phase ? t(PHASE_CHIP[setup.phase]) : "—"}</Chip>
							</div>
							{/* a register holding a production certificate is fixed for good */}
							<div className="linkrow" style={{ padding: 14 }}>
								<button
									type="button"
									disabled={embedded || r.status === "live"}
									title={r.status === "live" ? t("api.liveNoEdit") : undefined}
									onClick={() => navigate(`${paths.registers}?edit=${encodeURIComponent(r.id)}`)}
									className="link"
									style={{ border: "none", background: "none", padding: 0, color: "var(--brand)" }}
								>
									{t("common.edit")}
								</button>
								<button
									type="button"
									disabled={embedded || remove.isPending || r.status === "live"}
									title={r.status === "live" ? t("api.liveNoRemove") : undefined}
									onClick={() => remove.mutate(r.id)}
									className="link link--danger"
									style={{ border: "none", background: "none", padding: 0 }}
								>
									{t("common.delete")}
								</button>
							</div>
						</div>
					))}

					<div
						className="row"
						style={{ padding: "13px 14px", gap: 14, background: "var(--surface-2)" }}
					>
						<button
							type="button"
							disabled={embedded}
							onClick={() => navigate(paths.registers)}
							style={{
								border: "none",
								background: "none",
								padding: 0,
								cursor: "pointer",
								fontSize: 13,
								fontWeight: 600,
								color: "var(--brand)",
							}}
						>
							{t("review.addAnother")}
						</button>
						<div className="grow" />
						<div style={{ fontSize: 12, color: "var(--muted-2)" }}>
							{t("review.legalEntity", {
								company: setup.entity?.company ?? "—",
								tin: setup.entity?.tin ?? "—",
							})}
						</div>
					</div>
				</div>

				<div className="card col" style={{ padding: "22px 26px", gap: 18 }}>
					<button
						type="button"
						disabled={embedded || acknowledge.isPending}
						onClick={() => acknowledge.mutate(!setup.acknowledged)}
						aria-pressed={setup.acknowledged}
						style={{
							display: "flex",
							gap: 13,
							alignItems: "flex-start",
							border: "none",
							background: "none",
							padding: 0,
							cursor: embedded ? "default" : "pointer",
							textAlign: "start",
						}}
					>
						{setup.acknowledged ? (
							<Mark kind="square" size={19} font={12} style={{ marginTop: 1 }} />
						) : (
							<span
								className="checkbox"
								style={{ width: 19, height: 19, marginTop: 1, borderRadius: 4 }}
							/>
						)}
						<div className="pretty" style={{ fontSize: 13.5, lineHeight: 1.6, maxWidth: 900 }}>
							{t("review.ack")}
						</div>
					</button>
					<Rule />
					<div className="actions">
						<Btn
							size="lg"
							disabled={!setup.acknowledged || count === 0}
							busy={submit.isPending}
							title={setup.acknowledged ? undefined : t("review.ackFirst")}
							onClick={start}
						>
							{t(collectsOtp ? "review.continue" : "review.finish")}
						</Btn>
						<Btn size="lg" variant="secondary" onClick={() => navigate(paths.registers)}>
							{t("common.back")}
						</Btn>
						<div className="grow" />
						<div style={{ fontSize: 12.5, color: "var(--muted)" }}>
							{t(collectsOtp ? "review.next" : "review.nextPhase1")}
						</div>
					</div>
				</div>
			</div>
		</Page>
	);
}

function Stat({ n, label }: { n: number; label: string }) {
	return (
		<div className="col" style={{ gap: 2 }}>
			<div className="mono" style={{ fontSize: 20, fontWeight: 600 }}>
				{n}
			</div>
			<div style={{ fontSize: 11.5, color: "var(--muted-2)" }}>{label}</div>
		</div>
	);
}
