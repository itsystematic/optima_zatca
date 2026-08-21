import { useNavigate } from "react-router-dom";
import { Page } from "@/components/Page";
import { Checkbox, Eyebrow, Rule } from "@/components/primitives";
import { T, useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { useGuidance, useSetup } from "@/queries/setup";
import { stepPath, paths } from "./paths";

/** Guidance arrives from the server with stable keys; the copy is localised here. */
const localised = (key: string, suffix: string, fallback: string, t: (k: MessageKey) => string) => {
	const candidate = `${key}.${suffix}` as MessageKey;
	const value = t(candidate);
	return value === candidate ? fallback : value;
};

/** The actors the server names, mapped to copy. Anything else renders as sent. */
const ACTOR_KEY: Record<string, MessageKey> = {
	"this system": "lifecycle.actor.system",
	"the authority": "lifecycle.actor.authority",
};

/** 02 — the lifecycle as one scrollable page, then what to gather first. */
export function HowItWorks() {
	const navigate = useNavigate();
	const t = useT();
	const { data: guidance } = useGuidance();
	const { data: setup } = useSetup();

	const back = setup && setup.status !== "not_started" ? stepPath[setup.step] : paths.welcome;

	return (
		<Page
			width={1040}
			pad="0 40px"
			lead={
				<button type="button" className="linkbutton" onClick={() => navigate(back)}>
					← {t("common.close")}
				</button>
			}
		>
			<div
				className="col"
				style={{
					flex: "none",
					background: "var(--surface)",
					border: "1px solid var(--line)",
					borderBottom: "none",
					gap: 30,
					padding: "38px 64px 0",
				}}
			>
				<div className="col" style={{ gap: 10 }}>
					<Eyebrow tone="brand" size="lg">
						{t("howItWorks.eyebrow")}
					</Eyebrow>
					<h2 className="title" style={{ fontSize: 27, letterSpacing: "-.02em" }}>
						{t("howItWorks.title")}
					</h2>
				</div>

				{/* the connecting hairline sits behind the numbered discs */}
				<div style={{ position: "relative", padding: "6px 0 2px" }}>
					<div
						style={{
							position: "absolute",
							top: 23,
							insetInline: 22,
							height: 1,
							background: "var(--swatch)",
						}}
					/>
					<div style={{ display: "flex", position: "relative" }}>
						{(guidance?.lifecycle ?? []).map((s, i) => (
							<div
								key={s.key}
								className="col"
								style={{ flex: 1, gap: 12, alignItems: "flex-start", paddingInlineEnd: 14 }}
							>
								<div
									className="mono"
									style={{
										width: 44,
										height: 44,
										flex: "none",
										borderRadius: 10,
										background: "var(--surface)",
										border: "1px solid var(--brand-line)",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										fontSize: 14,
										fontWeight: 600,
										color: "var(--brand)",
										boxShadow: "0 0 0 5px var(--surface)",
									}}
								>
									{i + 1}
								</div>
								<div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.3 }}>
									{localised(`lifecycle.${s.key}`, "title", s.title, t)}
								</div>
								<div
									className="pretty"
									style={{ fontSize: 12, lineHeight: 1.5, color: "var(--muted)" }}
								>
									{localised(`lifecycle.${s.key}`, "body", s.body, t)}
								</div>
								<div
									className="mono"
									style={{
										fontSize: 10.5,
										color: "var(--brand)",
										background: "var(--brand-tint-2)",
										borderRadius: 3,
										padding: "2px 6px",
									}}
								>
									{ACTOR_KEY[s.actor] ? t(ACTOR_KEY[s.actor]) : s.actor}
								</div>
							</div>
						))}
					</div>
				</div>

				<Rule strong />

				<div
					style={{
						display: "grid",
						gridTemplateColumns: "1.35fr 1fr",
						gap: 44,
						paddingBottom: 44,
					}}
				>
					<div className="col" style={{ gap: 18 }}>
						<h3 className="title" style={{ fontSize: 19 }}>
							{t("howItWorks.checklist")}
						</h3>
						<div
							className="col"
							style={{ border: "1px solid var(--line)", borderRadius: 8, overflow: "hidden" }}
						>
							{(guidance?.checklist ?? []).map((c) => (
								<div
									key={c.key}
									style={{
										display: "flex",
										gap: 14,
										padding: "16px 18px",
										borderBottom: "1px solid var(--line-hair)",
										background: "var(--surface)",
									}}
								>
									<Checkbox size={18} style={{ marginTop: 1 }} />
									<div className="col" style={{ gap: 4 }}>
										<div style={{ fontSize: 13.5, fontWeight: 600 }}>
											{localised(`checklist.${c.key}`, "title", c.title, t)}
										</div>
										<div
											className="pretty"
											style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--muted)" }}
										>
											{localised(`checklist.${c.key}`, "body", c.body, t)}
										</div>
									</div>
								</div>
							))}
						</div>
					</div>

					<div className="col" style={{ gap: 14 }}>
						<div
							className="col"
							style={{
								background: "var(--surface-2)",
								border: "1px solid var(--line)",
								borderRadius: 8,
								padding: 20,
								gap: 10,
							}}
						>
							<Eyebrow>{t("howItWorks.otp.label")}</Eyebrow>
							<div
								className="pretty"
								style={{ fontSize: 13, lineHeight: 1.55, color: "var(--ink-2)" }}
							>
								<T k="howItWorks.otp.body" params={{ minutes: guidance?.otpTtlMinutes ?? 60 }} />
							</div>
							<a
								href={guidance?.portalUrl}
								target="_blank"
								rel="noreferrer"
								style={{ fontSize: 13, fontWeight: 600 }}
							>
								{t("howItWorks.otp.link")}
							</a>
						</div>
						<SideNote titleKey="howItWorks.key.title" bodyKey="howItWorks.key.body" />
						<SideNote titleKey="howItWorks.resume.title" bodyKey="howItWorks.resume.body" />
					</div>
				</div>
			</div>
		</Page>
	);
}

function SideNote({ titleKey, bodyKey }: { titleKey: MessageKey; bodyKey: MessageKey }) {
	const t = useT();
	return (
		<div
			className="col"
			style={{ border: "1px solid var(--line)", borderRadius: 8, padding: 20, gap: 8 }}
		>
			<div style={{ fontSize: 13.5, fontWeight: 600 }}>{t(titleKey)}</div>
			<div className="pretty" style={{ fontSize: 12.5, lineHeight: 1.55, color: "var(--muted)" }}>
				{t(bodyKey)}
			</div>
		</div>
	);
}
