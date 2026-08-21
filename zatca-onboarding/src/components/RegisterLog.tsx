import type { Register } from "@/api";
import { useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { useRegisterLog } from "@/queries/log";
import { FormError } from "./FormError";
import { Eyebrow } from "./primitives";

const OUTCOME_KEY: Record<string, MessageKey> = {
	ok: "log.outcome.ok",
	rejected: "log.outcome.rejected",
	error: "log.outcome.error",
	timeout: "log.outcome.timeout",
};

const TIME = new Intl.DateTimeFormat("en-GB", {
	hour: "2-digit",
	minute: "2-digit",
	second: "2-digit",
	hour12: false,
});

/**
 * Every exchange recorded for one register.
 *
 * Built to answer one question at a glance: which of the six compliance
 * documents was refused, and what did the authority say about it. The outcome
 * carries the colour, the refused rows are tinted, and the authority's own
 * wording is printed verbatim rather than paraphrased — a rule id like
 * `BR-KSA-44` is the thing worth searching for, and rewording it loses that.
 */
export function RegisterLog({ register, limit }: { register: Register | null; limit?: number }) {
	const t = useT();
	const { data: entries, isLoading, error } = useRegisterLog(register?.id ?? null, limit);

	if (!register) return null;
	if (error) return <div style={{ padding: 16 }}><FormError error={error} /></div>;

	if (isLoading) {
		return (
			<div className="col" style={{ gap: 1, padding: 16 }}>
				{[0, 1, 2].map((i) => (
					<div key={i} className="skeleton" style={{ height: 38 }} />
				))}
			</div>
		);
	}

	if (!entries?.length) return <div className="log__empty">{t("log.empty")}</div>;

	return (
		<div className="log">
			<div className="log__row log__head eyebrow" style={{ letterSpacing: ".11em" }}>
				<div>{t("log.col.at")}</div>
				<div>{t("log.col.operation")}</div>
				<div>{t("log.col.outcome")}</div>
				<div>{t("log.col.status")}</div>
				<div style={{ textAlign: "end" }}>{t("log.col.duration")}</div>
			</div>

			{entries.map((entry) => (
				<div key={entry.id} className="log__row" data-outcome={entry.outcome}>
					<div className="mono" style={{ color: "var(--muted)" }}>
						{TIME.format(new Date(entry.at))}
					</div>
					<div style={{ fontWeight: 500 }}>{entry.operation}</div>
					<div className="log__outcome" data-outcome={entry.outcome}>
						{t(OUTCOME_KEY[entry.outcome] ?? "log.outcome.error")}
					</div>
					<div className="mono" style={{ color: "var(--muted-2)" }}>
						{entry.httpStatus ?? "—"}
					</div>
					<div className="mono" style={{ textAlign: "end", color: "var(--muted-2)" }}>
						{duration(entry.durationMs, t)}
					</div>

					{entry.message && (
						<div className="log__message">
							<Eyebrow style={{ marginBottom: 4, color: "var(--danger-ink)" }}>
								{t("log.said")}
							</Eyebrow>
							{entry.message}
						</div>
					)}
				</div>
			))}
		</div>
	);
}

function duration(ms: number | null, t: (k: MessageKey, p?: Record<string, string | number>) => string) {
	if (ms === null) return "—";
	return ms >= 1000 ? t("log.seconds", { s: (ms / 1000).toFixed(1) }) : t("log.ms", { ms });
}
