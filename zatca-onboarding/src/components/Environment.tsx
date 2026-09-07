import type { Environment } from "@/api";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { cx } from "./primitives";

/**
 * Which authority a registration talks to.
 *
 * Sandbox, simulation and production are not interchangeable: a certificate
 * issued in one is refused by the others, and an invoice sent anywhere but
 * production has no legal effect. Someone who cannot see this will eventually
 * believe they are filing when they are not, so it is stated wherever a
 * consequence follows — and never guessed when the server does not say.
 */

export const isLive = (env: Environment | null): boolean => env === "production";

/**
 * The persistent marker in the page strip.
 *
 * With `detail`, the marker carries the full notice and reveals it on hover or
 * keyboard focus. That notice used to sit as a banner at the top of the review
 * and done screens, where it was the largest thing on the page every time —
 * including the ninth time, and including for the people who chose the sandbox
 * deliberately. Attaching it to the badge keeps the fact one glance away without
 * spending a block of the screen restating it.
 *
 * The badge itself never disappears, because that is the part that must not be
 * missable: what is hidden is the paragraph, not the environment.
 *
 * A `<button>` rather than a hovered `<span>`: a tooltip that only a mouse can
 * open is unreachable by keyboard and invisible to a screen reader, and this one
 * says whether the operator's invoices count.
 */
export function EnvironmentMarker({
	environment,
	detail = false,
}: {
	environment: Environment | null;
	detail?: boolean;
}) {
	const t = useT();
	if (!environment) return null;

	const badge = (
		<>
			<span className="envmark__dot" />
			{t(`env.${environment}.name` as MessageKey)}
		</>
	);

	if (!detail) {
		return (
			<span
				className={cx("envmark", isLive(environment) && "envmark--live")}
				title={t(`env.${environment}.short` as MessageKey)}
			>
				{badge}
			</span>
		);
	}

	const describedBy = `envmark-detail-${environment}`;

	return (
		<span className="envmark-wrap">
			<button
				type="button"
				className={cx("envmark", "envmark--button", isLive(environment) && "envmark--live")}
				aria-describedby={describedBy}
			>
				{badge}
			</button>
			<span className="envmark__pop" id={describedBy} role="tooltip">
				<EnvironmentNotice environment={environment} />
			</span>
		</span>
	);
}

/**
 * The unmissable version, for the two screens where the operator is deciding
 * whether to commit or believing they are finished.
 */
export function EnvironmentNotice({ environment }: { environment: Environment | null }) {
	const t = useT();

	if (!environment) {
		return (
			<div className="envnotice envnotice--unknown" role="note">
				<div className="envnotice__title">{t("env.label")}</div>
				<div className="envnotice__body">{t("env.unknown")}</div>
			</div>
		);
	}

	const live = isLive(environment);
	return (
		<div className={cx("envnotice", live ? "envnotice--live" : "envnotice--test")} role="note">
			<div className="envnotice__title">
				{t(`env.${environment}.name` as MessageKey)} · {t(`env.${environment}.short` as MessageKey)}
			</div>
			<div className="envnotice__body">
				<T k={`env.${environment}.long` as MessageKey} />
			</div>
		</div>
	);
}
