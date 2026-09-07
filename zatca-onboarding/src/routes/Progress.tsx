import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Register, Setup, StageState } from "@/api";
import { STAGE_KEYS } from "@/api";
import { Page } from "@/components/Page";
import { RegisterLog } from "@/components/RegisterLog";
import { StageBar } from "@/components/StageBar";
import { OtpInput } from "@/components/inputs";
import { FormError } from "@/components/FormError";
import { Btn, Mark, Spinner } from "@/components/primitives";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { formatDateTime, mmss } from "@/lib/format";
import { OTP_LENGTH } from "@/lib/validation";
import { useFinishWithLive, useRetryRegisters } from "@/queries/setup";
import { useRunningSetup } from "@/queries/run";
import { paths } from "./paths";

/**
 * A retry resumes from the compliance certificate when the register got that
 * far. If it did not, the authority wants a fresh one-time password, so the
 * panel has to collect one before the retry can be sent.
 */
function needsFreshCode(register: Register): boolean {
	return register.run?.stages.compliance !== "done";
}

/**
 * 10 / 11 — the run.
 *
 * One screen, two states: while work is outstanding it is a live progress board;
 * once everything settles with a failure it becomes the recovery screen. Motion
 * is confined to the single stage that is actually moving.
 */
export function Progress() {
	const navigate = useNavigate();
	const t = useT();
	const { data: setup } = useRunningSetup();
	// the log opens over the board rather than navigating away: the run is still
	// moving, and losing sight of it to read one register's detail is a poor trade
	const [logFor, setLogFor] = useState<string | null>(null);

	// an entirely clean run needs no decision from anyone
	useEffect(() => {
		if (setup?.completedAt) navigate(paths.done, { replace: true });
	}, [setup?.completedAt, navigate]);

	if (!setup) return null;

	const running = setup.status === "running";
	const live = setup.registers.filter((r) => r.status === "live");
	const failed = setup.registers.filter((r) => r.status === "failed");
	const inFlight = setup.registers.filter((r) => r.status === "running" || r.status === "queued");
	const logRegister = setup.registers.find((r) => r.id === logFor) ?? null;

	return (
		<Page
			guide="progress"
			width={1160}
			pad={running ? "24px 40px 30px" : "20px 40px 26px"}
			status={
				running ? (
					<span className="mono" style={{ fontSize: 11.5, color: "var(--warn)" }}>
						{t("progress.elapsed", { time: mmss(elapsedSeconds(setup)) })}
					</span>
				) : (
					<span style={{ fontSize: 11.5, color: "var(--danger)", fontWeight: 600 }}>
						{t("progress.status.finished", { count: failed.length })}
					</span>
				)
			}
		>
			<div className="col" style={{ gap: running ? 20 : 18 }}>
				{running ? (
					<RunningHeader setup={setup} live={live.length} inFlight={inFlight.length} />
				) : (
					<SettledHeader live={live.length} failed={failed.length} total={setup.registers.length} />
				)}

				{/*
				 * Sized by its contents, not by what is left on screen.
				 *
				 * `flex: 1` gave this card exactly the space remaining and
				 * `overflow: hidden` — which is there to clip the rows to the
				 * rounded corners — then cut off anything taller. Expanding the
				 * failure detail on two registers put the second one past the edge
				 * with no way to scroll to it; the only way to read it was to
				 * collapse the first. Letting the card grow hands the scrolling
				 * back to the page, which is where it belongs.
				 */}
				<div className="card col" style={{ overflow: "hidden" }}>
					{running && (
						<div
							className="row eyebrow"
							style={{
								padding: "11px 24px",
								background: "var(--surface-2)",
								borderBottom: "1px solid var(--line)",
								letterSpacing: ".11em",
								color: "var(--muted)",
							}}
						>
							<div style={{ width: 270 }}>{t("progress.col.register")}</div>
							<div className="grow">{t("progress.col.chain")}</div>
							<div style={{ width: 210 }}>{t("progress.col.status")}</div>
							<div style={{ width: 96 }} />
						</div>
					)}

					{setup.registers.map((r, i) =>
						r.status === "failed" ? (
							<FailedRow key={r.id} register={r} onOpenLog={() => setLogFor(r.id)} />
						) : (
							<RunRow
								key={r.id}
								register={r}
								running={running}
								last={i === setup.registers.length - 1}
								onOpenLog={() => setLogFor(r.id)}
							/>
						),
					)}

					<div
						className="row"
						style={{
							marginTop: "auto",
							padding: running ? "16px 24px" : "18px 24px",
							background: "var(--surface-2)",
							borderTop: "1px solid var(--line)",
							gap: 16,
						}}
					>
						{running ? (
							<>
								<div style={{ fontSize: 12.5, color: "var(--muted)" }}>
									{t("progress.independent")}
								</div>
								<div className="grow" />
								<a href="#" className="link link--quiet">
									{t("progress.fullLog")}
								</a>
							</>
						) : (
							<SettledFooter failed={failed} live={live.length} />
						)}
					</div>
				</div>
			</div>

			<LogDrawer register={logRegister} onClose={() => setLogFor(null)} />
		</Page>
	);
}

/** One register's exchanges, over the run rather than instead of it. */
function LogDrawer({ register, onClose }: { register: Register | null; onClose: () => void }) {
	const t = useT();
	if (!register) return null;

	return (
		<>
			<div className="drawer__scrim" onClick={onClose} />
			<aside
				className="drawer"
				role="dialog"
				aria-modal="true"
				aria-label={t("log.openFor", { name: register.registerName })}
			>
				<div className="drawer__head">
					<div className="col" style={{ gap: 3, flex: 1 }}>
						<div style={{ fontSize: 16, fontWeight: 600 }}>{register.registerName}</div>
						<div className="mono" style={{ fontSize: 11.5, color: "var(--muted-2)" }}>
							{register.crn}
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						aria-label={t("log.close")}
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
				<div className="drawer__body">
					<RegisterLog register={register} />
				</div>
			</aside>
		</>
	);
}

function elapsedSeconds(setup: Setup): number {
	return setup.startedAt ? (Date.now() - Date.parse(setup.startedAt)) / 1000 : 0;
}

/**
 * The status column, written here rather than by the server.
 *
 * The backend reports which stage is moving and how far in; turning that into a
 * sentence is a presentation job, and doing it client-side is what lets the
 * column translate.
 */
function useRunLine() {
	const t = useT();
	return (register: Register): { text: string; detail: string } => {
		const run = register.run;
		if (!run || register.status === "queued") {
			return { text: t("run.queued"), detail: t("run.queuedDetail") };
		}
		const time = mmss(run.elapsedSeconds);
		if (register.status === "live") {
			return { text: t("run.done"), detail: t("run.completedIn", { time }) };
		}
		const detail = t("run.stageOf", { n: run.stageIndex, total: STAGE_KEYS.length, time });
		if (register.status === "failed") {
			return { text: t(`run.failedAt.${run.stage}` as MessageKey), detail };
		}
		return {
			text: t(`run.stage.${run.stage}` as MessageKey, { n: run.testInvoice ?? 1 }),
			detail,
		};
	};
}

/* ── Headers ────────────────────────────────────────────────────────────── */

function RunningHeader({
	setup,
	live,
	inFlight,
}: {
	setup: Setup;
	live: number;
	inFlight: number;
}) {
	const t = useT();
	const total = setup.registers.length;
	return (
		<div className="card row" style={{ padding: "24px 28px", gap: 28 }}>
			<div className="col" style={{ gap: 6, flex: 1 }}>
				<h2 className="title" style={{ fontSize: 22, letterSpacing: "-.018em" }}>
					{t("progress.title", { count: total })}
				</h2>
				<div style={{ fontSize: 13.5, color: "var(--muted)" }}>{t("progress.leave")}</div>
			</div>
			<div className="col" style={{ gap: 8, width: 300 }}>
				<div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
					<div className="mono" style={{ fontSize: 22, fontWeight: 600 }}>
						{live}
					</div>
					<div style={{ fontSize: 13, color: "var(--muted)" }}>
						{t("progress.complete", { total })}
					</div>
					<div className="grow" />
					<div className="mono" style={{ fontSize: 11.5, color: "var(--warn)" }}>
						{t("progress.running", { count: inFlight })}
					</div>
				</div>
				<div className="meter">
					<div className="meter__done" style={{ width: `${(live / total) * 100}%` }} />
					<div className="meter__run" style={{ width: `${(inFlight / total) * 100}%` }} />
				</div>
				<div style={{ fontSize: 11.5, color: "var(--muted-2)" }}>{t("progress.eta")}</div>
			</div>
		</div>
	);
}

function SettledHeader({ live, failed, total }: { live: number; failed: number; total: number }) {
	const t = useT();
	return (
		<div className="card row" style={{ padding: "22px 26px", gap: 28 }}>
			<div className="col" style={{ gap: 5, flex: 1 }}>
				<h2 className="title" style={{ fontSize: 21, letterSpacing: "-.018em" }}>
					{t("progress.settled.live", { count: live })}{" "}
					{t("progress.settled.failed", { count: failed })}
				</h2>
				<div style={{ fontSize: 13.5, color: "var(--muted)" }}>
					{t("progress.settled.body", { count: live, live })}
				</div>
			</div>
			<div className="col" style={{ gap: 8, width: 300 }}>
				<div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
					<div className="mono" style={{ fontSize: 22, fontWeight: 600 }}>
						{live}
					</div>
					<div style={{ fontSize: 13, color: "var(--muted)" }}>
						{t("progress.complete", { total })}
					</div>
					<div className="grow" />
					<div className="mono" style={{ fontSize: 11.5, color: "var(--danger)", fontWeight: 600 }}>
						{t("progress.failedCount", { count: failed })}
					</div>
				</div>
				<div className="meter">
					<div className="meter__done" style={{ width: `${(live / total) * 100}%` }} />
					<div className="meter__fail" style={{ width: `${(failed / total) * 100}%` }} />
				</div>
			</div>
		</div>
	);
}

/* ── Rows ───────────────────────────────────────────────────────────────── */

function stageList(register: Register): StageState[] {
	const stages = register.run?.stages;
	if (!stages) return STAGE_KEYS.map(() => "idle");
	return STAGE_KEYS.map((k) => stages[k]);
}

function RunRow({
	register,
	running,
	last,
	onOpenLog,
}: {
	register: Register;
	running: boolean;
	last: boolean;
	onOpenLog: () => void;
}) {
	const t = useT();
	const line = useRunLine()(register);
	const busy = register.status === "running" || register.status === "queued";

	return (
		<div
			className="row"
			style={{
				padding: running ? "20px 24px" : "15px 24px",
				borderBottom: last && !running ? undefined : "1px solid var(--line-hair)",
				gap: 16,
				// the wash marks a row doing work; the last row abuts the footer
				background: busy && !last ? "var(--warn-tint)" : undefined,
			}}
		>
			<div className="row" style={{ width: 254, gap: 12 }}>
				{busy ? (
					<Spinner size={running ? 22 : 20} />
				) : (
					<Mark kind="tick-solid" size={running ? 22 : 20} font={running ? 12 : 11} />
				)}
				<div className="col" style={{ gap: 2 }}>
					<div style={{ fontSize: 13.5, fontWeight: 600 }}>{register.registerName}</div>
					{running && (
						<div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
							{register.crn}
						</div>
					)}
				</div>
			</div>

			<StageBar
				stages={stageList(register)}
				runPct={register.run?.stageProgress ?? 0}
				slim={!running}
			/>

			{running ? (
				<div className="col" style={{ width: 210, gap: 3 }}>
					<div style={{ fontSize: 13, fontWeight: 600, color: busy ? "var(--warn)" : "var(--ok)" }}>
						{line.text}
					</div>
					<div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
						{line.detail}
					</div>
				</div>
			) : (
				<div style={{ width: 210, fontSize: 12.5, fontWeight: 600, color: "var(--ok)" }}>
					{t("common.live")}
				</div>
			)}

			<div style={{ width: 96, textAlign: "end" }}>
				<button type="button" onClick={onOpenLog} className="linkbutton link--quiet">
					{t("common.viewLog")}
				</button>
			</div>
		</div>
	);
}

function FailedRow({ register, onOpenLog }: { register: Register; onOpenLog: () => void }) {
	const t = useT();
	const line = useRunLine()(register);
	const [open, setOpen] = useState(true);
	const [code, setCode] = useState("");
	const retry = useRetryRegisters();
	const error = register.run?.error;

	const wantsCode = needsFreshCode(register);
	const canRetry = !wantsCode || code.length === OTP_LENGTH;

	const send = () =>
		retry.mutate({
			ids: [register.id],
			entries: wantsCode ? [{ registerId: register.id, code }] : [],
		});

	return (
		<div
			style={{
				borderBottom: "1px solid var(--line-hair)",
				background: "var(--danger-tint)",
				borderInlineStart: "3px solid var(--danger)",
			}}
		>
			<div className="row" style={{ padding: "15px 24px", gap: 16 }}>
				<div className="row" style={{ width: 251, gap: 12 }}>
					<Mark kind="fail" size={20} font={12} />
					<div className="col" style={{ gap: 2 }}>
						<div style={{ fontSize: 13.5, fontWeight: 600 }}>{register.registerName}</div>
						<div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
							{register.crn}
						</div>
					</div>
				</div>
				<StageBar stages={stageList(register)} slim />
				<div className="col" style={{ width: 210, gap: 2 }}>
					<div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--danger)" }}>{line.text}</div>
					<div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
						{line.detail}
					</div>
				</div>
				<div style={{ width: 96, textAlign: "end" }}>
					<button
						type="button"
						onClick={() => setOpen((v) => !v)}
						aria-expanded={open}
						className="link link--danger"
						style={{ border: "none", background: "none", padding: 0 }}
					>
						{t(open ? "progress.hideDetail" : "progress.showDetail")}
					</button>
				</div>
			</div>

			{open && error && (
				<div className="col" style={{ padding: "0 24px 20px 47px", gap: 14 }}>
					<div className="pretty" style={{ fontSize: 13.5, lineHeight: 1.55, maxWidth: 820 }}>
						<b>{t(`error.${error.code}.summary` as MessageKey)}</b>{" "}
						{t(`error.${error.code}.remedy` as MessageKey)}
					</div>

					<div
						style={{
							background: "var(--surface)",
							border: "1px solid var(--danger-line)",
							borderRadius: 8,
							overflow: "hidden",
						}}
					>
						<div
							className="row"
							style={{
								padding: "9px 14px",
								background: "var(--danger-tint-2)",
								borderBottom: "1px solid var(--danger-line)",
								gap: 10,
							}}
						>
							<div className="eyebrow" style={{ letterSpacing: ".11em", color: "var(--danger-ink)" }}>
								{t("progress.technical")}
							</div>
							<div className="grow" />
							<div className="mono" style={{ fontSize: 10.5, color: "var(--muted-2)" }}>
								{formatDateTime(error.occurredAt)}
							</div>
						</div>
						{/* the raw exchange, deliberately left in the wire's own language */}
						<div
							className="mono"
							dir="ltr"
							style={{
								padding: 14,
								fontSize: 11.5,
								lineHeight: 1.75,
								color: "#3D4147",
								whiteSpace: "pre",
								textAlign: "left",
							}}
						>
							<div>
								{error.endpoint} →{" "}
								<span style={{ color: "var(--danger)", fontWeight: 600 }}>
									{error.httpStatus} {httpText(error.httpStatus)}
								</span>
							</div>
							{[
								["code", error.code],
								...Object.entries(error.details),
								["req_id", error.requestId],
								[
									"attempt",
									t("error.attempt", { attempt: error.attempt, max: error.maxAttempts }),
								],
							].map(([k, v]) => (
								<div key={k}>
									{k.padEnd(8)}: {v}
								</div>
							))}
						</div>
					</div>

					{wantsCode && (
						<div className="col" style={{ gap: 7 }}>
							<div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
								<label style={{ fontSize: 12.5, fontWeight: 600 }}>
									{t("progress.retryOtp.label")}
								</label>
								<span style={{ fontSize: 11.5, color: "var(--muted)" }}>
									{t("progress.retryOtp.hint")}
								</span>
							</div>
							<OtpInput
								label={t("otp.group", { name: register.registerName })}
								digitLabel={(n) => t("otp.digit", { name: register.registerName, n })}
								value={code}
								onChange={setCode}
							/>
						</div>
					)}

					<FormError error={retry.error} />

					<div className="row" style={{ gap: 12 }}>
						<Btn size="sm" busy={retry.isPending} disabled={!canRetry} onClick={send}>
							{t("progress.retryThis")}
						</Btn>
						<Btn size="sm" variant="secondary" onClick={onOpenLog}>
							{t("common.viewLog")}
						</Btn>
						<Btn
							size="sm"
							variant="secondary"
							onClick={() => navigator.clipboard?.writeText(JSON.stringify(error, null, 2))}
						>
							{t("progress.copyDiagnostics")}
						</Btn>
						<a href="#" style={{ fontSize: 13, fontWeight: 600 }}>
							{t("progress.newOtp")}
						</a>
					</div>
				</div>
			)}
		</div>
	);
}

function httpText(status: number): string {
	return status === 400
		? "Bad Request"
		: status === 401
			? "Unauthorized"
			: status === 403
				? "Forbidden"
				: "Error";
}

/* ── Settled footer ─────────────────────────────────────────────────────── */

function SettledFooter({ failed, live }: { failed: Register[]; live: number }) {
	const navigate = useNavigate();
	const t = useT();
	const finish = useFinishWithLive();
	const retry = useRetryRegisters();
	const names = failed.map((r) => r.registerName.split("—")[0].trim()).join("، ");

	// retrying everything at once only works while none of them wants a new code;
	// those are retried one at a time, from their own panel
	const blocked = failed.some(needsFreshCode);

	return (
		<>
			<Btn
				style={{ padding: "12px 22px" }}
				busy={finish.isPending}
				onClick={() => finish.mutate(undefined as never, { onSuccess: () => navigate(paths.done) })}
			>
				{t("progress.continueWith", { count: live })}
			</Btn>
			{!blocked && (
				<Btn
					variant="secondary"
					style={{ padding: "12px 18px" }}
					busy={retry.isPending}
					onClick={() => retry.mutate({ ids: failed.map((r) => r.id) })}
				>
					{t("progress.retryAll")}
				</Btn>
			)}
			<div className="grow" />
			<div className="col" style={{ gap: 8, maxWidth: 420, alignItems: "flex-end" }}>
				<FormError error={finish.error ?? retry.error} />
				<div style={{ fontSize: 12.5, color: "var(--muted)", textAlign: "end" }}>
					<T k="progress.draftNote" params={{ count: failed.length, names }} />
				</div>
			</div>
		</>
	);
}
