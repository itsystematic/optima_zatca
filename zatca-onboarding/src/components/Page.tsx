import type { CSSProperties, ReactNode } from "react";
import { LANGUAGES, useI18n } from "@/i18n/core";
import { ITSystematicMark } from "./Marks";
import { Guide, type GuideStep } from "./Guide";
import { EnvironmentMarker } from "./Environment";
import { useSetup } from "@/queries/setup";
import { cx } from "./primitives";

/**
 * The frame every screen sits in.
 *
 * This app is served on its own route rather than inside the desk, so the strip
 * across the top is the only chrome there is. It carries the mark in the leading
 * corner — present on every screen, so the operator can always see whose software
 * is asking them for a tax number — then whatever status the screen has to
 * report, the environment badge and the language switch, above a centred content
 * column at the width the design specifies.
 */
export function Page({
	width = 1040,
	/** status for this screen: autosave, run timer, a live badge */
	status,
	/** a leading control, such as the close link on the explainer */
	lead,
	/**
	 * Which step's guidance to show above the content.
	 *
	 * Rendered here rather than by each screen so it lands in the same place on
	 * every one of them — a panel that drifts between steps reads as nine
	 * different things rather than one recurring one.
	 */
	guide,
	/** vertically centre the column, for the hero */
	center = false,
	pad = "32px 40px",
	children,
	style,
}: {
	width?: number;
	status?: ReactNode;
	lead?: ReactNode;
	guide?: GuideStep;
	center?: boolean;
	pad?: string;
	children: ReactNode;
	style?: CSSProperties;
}) {
	const { dir } = useI18n();

	return (
		<div className="page" dir={dir}>
			<div className="page__strip">
				<ITSystematicMark size={42} title="IT Systematic" />
				{lead}
				<div className="grow" />
				{status}
				<SetupEnvironment />
				<LanguageSwitch />
			</div>
			<div className={cx("page__body", center && "page__body--center")} style={{ padding: pad }}>
				<div className="page__column" style={{ width, ...style }}>
					{guide && <Guide step={guide} />}
					{children}
				</div>
			</div>
		</div>
	);
}

/**
 * Which authority this company is registered against, on every screen.
 *
 * Read from the setup record rather than passed down: it is true of the whole
 * session, and a marker that appears on only some screens is worse than none —
 * its absence would read as "this one is different".
 */
function SetupEnvironment() {
	const { data: setup } = useSetup();
	return <EnvironmentMarker detail environment={setup?.environment ?? null} />;
}

/** EN / ع, the one piece of chrome this app owns. */
export function LanguageSwitch() {
	const { lang, setLang, t } = useI18n();
	return (
		<div className="langswitch" role="group" aria-label={t("common.language")}>
			{LANGUAGES.map((l) => (
				<button
					key={l.code}
					type="button"
					lang={l.code}
					aria-label={l.label}
					aria-pressed={lang === l.code}
					className={cx(l.code === "ar" && "ar")}
					onClick={() => setLang(l.code)}
				>
					{l.native}
				</button>
			))}
		</div>
	);
}
