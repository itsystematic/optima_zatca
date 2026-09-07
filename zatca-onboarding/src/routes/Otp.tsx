import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { OtpInput } from "@/components/inputs";
import { Btn } from "@/components/primitives";
import { useT } from "@/i18n/core";
import { T } from "@/i18n/core";
import { FormError } from "@/components/FormError";
import { Guide } from "@/components/Guide";
import { OTP_LENGTH } from "@/lib/validation";
import { useGuidance, useSetup, useSubmitOtp } from "@/queries/setup";
import { Review } from "./Review";
import { paths } from "./paths";

/**
 * 09 — one labelled six-segment input per register, so nobody has to remember
 * which code belongs to which branch. Drawn over the review page it interrupts.
 */
export function Otp() {
	const navigate = useNavigate();
	const t = useT();
	const { data: setup } = useSetup();
	const { data: guidance } = useGuidance();
	const submit = useSubmitOtp();
	const [codes, setCodes] = useState<Record<string, string>>({});

	if (!setup) return null;

	const registers = setup.registers;
	const entered = registers.filter((r) => (codes[r.id] ?? "").length === OTP_LENGTH);
	const firstMissing = registers.find((r) => (codes[r.id] ?? "").length !== OTP_LENGTH);
	const ready = entered.length === registers.length && registers.length > 0;

	const confirm = () =>
		submit.mutate(
			{ entries: registers.map((r) => ({ registerId: r.id, code: codes[r.id] ?? "" })) },
			{ onSuccess: () => navigate(paths.progress) },
		);

	return (
		// fills the shell so the scrim and the centred dialog cover the whole viewport
		<div style={{ position: "relative", flex: 1, minHeight: 0, display: "flex" }}>
			{/* the page the modal interrupted, still legible behind the scrim */}
			<Review embedded />

			<div
				style={{ position: "absolute", inset: 0, background: "rgba(1, 0, 43, .46)" }}
				onClick={() => navigate(paths.review)}
			/>

			<div
				role="dialog"
				aria-modal="true"
				aria-label={t("otp.title")}
				style={{
					position: "absolute",
					inset: 0,
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					padding: 40,
					pointerEvents: "none",
				}}
			>
				<div
					className="col"
					style={{
						width: 760,
						maxHeight: "100%",
						background: "var(--surface)",
						borderRadius: 12,
						boxShadow: "var(--shadow-modal)",
						overflow: "hidden",
						pointerEvents: "auto",
					}}
				>
					<header
						className="col"
						style={{
							padding: "26px 32px 20px",
							gap: 8,
							borderBottom: "1px solid var(--line-hair)",
							flex: "none",
						}}
					>
						<div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
							<div className="col" style={{ flex: 1, gap: 7 }}>
								<h2 className="title" style={{ fontSize: 21, letterSpacing: "-.015em" }}>
									{t("otp.title")}
								</h2>
								<div
									className="pretty"
									style={{ fontSize: 13.5, lineHeight: 1.55, color: "var(--muted)" }}
								>
									<T k="otp.body" params={{ minutes: guidance?.otpTtlMinutes ?? 60 }} />{" "}
									<a href={guidance?.portalUrl} target="_blank" rel="noreferrer" style={{ fontWeight: 600 }}>
										{t("otp.where")}
									</a>
								</div>
							</div>
							<button
								type="button"
								onClick={() => navigate(paths.review)}
								aria-label={t("common.close")}
								style={{
									border: "none",
									background: "none",
									cursor: "pointer",
									fontSize: 18,
									color: "var(--muted-2)",
									lineHeight: 1,
								}}
							>
								✕
							</button>
						</div>
						{/* the dialog is its own screen, so it carries its own guidance */}
						<Guide step="otp" />
					</header>

					<div className="col" style={{ padding: "8px 32px", overflowY: "auto" }}>
						{registers.map((r, i) => {
							const code = codes[r.id] ?? "";
							const done = code.length === OTP_LENGTH;
							return (
								<div
									key={r.id}
									className="row"
									style={{
										gap: 20,
										padding: "16px 0",
										borderBottom: "1px solid var(--line-hair-2)",
									}}
								>
									<div className="col" style={{ flex: 1, gap: 3 }}>
										<div style={{ fontSize: 13.5, fontWeight: 600 }}>{r.registerName}</div>
										<div className="mono" style={{ fontSize: 11.5, color: "var(--muted-2)" }}>
											{t("otp.cr", { crn: r.crn })}
										</div>
									</div>
									<OtpInput
										label={t("otp.group", { name: r.registerName })}
										digitLabel={(n) => t("otp.digit", { name: r.registerName, n })}
										value={code}
										autoFocus={i === 0}
										onChange={(next) => setCodes((c) => ({ ...c, [r.id]: next }))}
									/>
									<div
										style={{
											width: 92,
											fontSize: 11.5,
											color: done ? "var(--ok)" : "var(--muted-2)",
											textAlign: "end",
										}}
									>
										{t(done ? "otp.complete" : "otp.waiting")}
									</div>
								</div>
							);
						})}
					</div>

					<div style={{ padding: submit.isError ? "12px 32px 0" : 0 }}>
						<FormError error={submit.error} />
					</div>

					<footer
						className="row"
						style={{
							padding: "20px 32px 24px",
							background: "var(--surface-2)",
							borderTop: "1px solid var(--line-hair)",
							gap: 16,
							flex: "none",
						}}
					>
						<Btn disabled={!ready} busy={submit.isPending} onClick={confirm}>
							{t("otp.confirm")}
						</Btn>
						<Btn variant="secondary" onClick={() => navigate(paths.review)}>
							{t("common.cancel")}
						</Btn>
						<div className="grow" />
						<div className="col" style={{ gap: 3, alignItems: "flex-end" }}>
							<div
								className="mono"
								style={{
									fontSize: 12,
									fontWeight: 600,
									color: ready ? "var(--ok)" : "var(--warn)",
								}}
							>
								{t("otp.entered", { done: entered.length, total: registers.length })}
							</div>
							<div style={{ fontSize: 11.5, color: "var(--muted-2)" }}>
								{firstMissing
									? t("otp.enterNext", { name: shortName(firstMissing.registerName) })
									: t("otp.allEntered")}
							</div>
						</div>
					</footer>
				</div>
			</div>
		</div>
	);
}

/** "Khobar — Showroom" reads better as just "Khobar" in a one-line prompt. */
function shortName(name: string): string {
	return name.split("—")[0].trim();
}
