import { useNavigate } from "react-router-dom";
import { Page } from "@/components/Page";
import {
	CertificateAuthorityMark,
	CommerceMark,
	TaxAuthorityMark,
	ITSystematicLogo,
} from "@/components/Marks";
import { Btn, Eyebrow } from "@/components/primitives";
import { Skyline } from "@/components/Skyline";
import { T, useT } from "@/i18n/core";
import { useSetup } from "@/queries/setup";
import { effectiveStep, stepPath, paths } from "./paths";

const AUTHORITIES = [
	{ key: "welcome.authorities.tax", Mark: TaxAuthorityMark },
	{ key: "welcome.authorities.commerce", Mark: CommerceMark },
	{ key: "welcome.authorities.ca", Mark: CertificateAuthorityMark },
] as const;

/** 01 — one promise, one action, and the marks that say this is a legal filing. */
export function Welcome() {
	const navigate = useNavigate();
	const t = useT();
	const { data: setup } = useSetup();

	// three honest states: never started, part-way through, already registered
	const cta =
		!setup || setup.status === "not_started"
			? "welcome.start"
			: setup.completedAt
				? "welcome.view"
				: "welcome.resume";
	// A fresh setup starts at the company, not at the obligation: every answer
	// that follows is stored against one, so it is settled before any is asked.
	// A setup already under way resumes where it actually is.
	const target =
		setup && setup.status !== "not_started" ? stepPath[effectiveStep(setup)] : paths.company;

	return (
		<Page center width={1040} pad="24px 40px 48px">
			<div className="card" style={{ boxShadow: "var(--shadow-card)" }}>
				<div className="col" style={{ padding: "64px 80px 56px", gap: 26 }}>
					<Eyebrow tone="brand" size="lg" style={{ letterSpacing: ".16em" }}>
						{t("welcome.eyebrow")}
					</Eyebrow>
					<h1
						className="pretty"
						style={{
							margin: 0,
							fontSize: 44,
							lineHeight: 1.08,
							fontWeight: 600,
							letterSpacing: "-.025em",
							maxWidth: 740,
						}}
					>
						{t("welcome.title")}
					</h1>
					<p
						className="pretty"
						style={{ margin: 0, fontSize: 17, lineHeight: 1.6, color: "var(--ink-2)", maxWidth: 640 }}
					>
						{t("welcome.body")}
					</p>
					<div className="actions" style={{ marginTop: 6 }}>
						<Btn size="lg" onClick={() => navigate(target)}>
							{t(cta)}
						</Btn>
						<Btn size="lg" variant="secondary" onClick={() => navigate(paths.howItWorks)}>
							{t("welcome.howItWorks")}
						</Btn>
					</div>
					<div
						className="mono"
						style={{ display: "flex", gap: 22, fontSize: 11.5, color: "var(--muted)", marginTop: 4 }}
					>
						<span>{t("welcome.meta.duration")}</span>
						<span style={{ color: "var(--line-strong)" }}>|</span>
						<span>{t("welcome.meta.otp")}</span>
						<span style={{ color: "var(--line-strong)" }}>|</span>
						<span>{t("welcome.meta.reversible")}</span>
					</div>
				</div>

				{/* the horizon this filing is made under, between the ask and the seals */}
				<Skyline height={132} />

				<footer
					className="col"
					style={{
						borderTop: "1px solid var(--line)",
						background: "var(--surface-2)",
						padding: "26px 80px",
						gap: 16,
					}}
				>
					<Eyebrow style={{ letterSpacing: ".14em" }}>{t("welcome.authorities.label")}</Eyebrow>
					<div className="row" style={{ gap: 40, flexWrap: "wrap" }}>
						{AUTHORITIES.map(({ key, Mark }) => (
							<div key={key} className="row" style={{ gap: 11 }}>
								<Mark size={30} />
								<div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink-2)" }}>
									<T k={key} />
								</div>
							</div>
						))}
						<div className="grow" />
						{/* the app's own mark sits last, after the bodies it answers to */}
						<ITSystematicLogo size={22} />
					</div>
				</footer>
			</div>
		</Page>
	);
}
