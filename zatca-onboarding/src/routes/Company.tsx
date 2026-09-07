import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { Company as CompanyRecord } from "@/api";
import { Page } from "@/components/Page";
import { ChoiceCard } from "@/components/inputs";
import { Btn, Chip, Eyebrow, Radio, Rule } from "@/components/primitives";
import { useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { useCompanies, useSwitchCompany } from "@/queries/setup";
import { paths } from "./paths";

/**
 * 00 — which company is being registered.
 *
 * First, because a setup belongs to a company: every later answer is stored
 * against one, and changing it is not editing this record but opening another's.
 * Asking here costs one screen; asking later meant discovering three answers in
 * that they belonged to the wrong company, and re-entering them.
 *
 * Skipped entirely when the site has one company — there is nothing to decide,
 * and a screen with a single option is a screen that only wastes a click.
 */
export function Company() {
	const navigate = useNavigate();
	const t = useT();
	const { data: companies, isLoading } = useCompanies();
	const switchCompany = useSwitchCompany();

	const only = companies?.length === 1 ? companies[0] : undefined;

	// One company is not a choice. Take it and move on, without rendering a
	// screen the operator would only have to dismiss.
	useEffect(() => {
		if (!only) return;
		switchCompany(only.name);
		navigate(paths.mode, { replace: true });
		// switchCompany is stable per render but not referentially, and re-running
		// this would reset the cache under a screen already past it
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [only, navigate]);

	if (isLoading || only) return null;

	const choose = (company: CompanyRecord) => {
		if (!company.eligible) return;
		switchCompany(company.name);
		// a company already registered has nothing left to answer, so send the
		// operator to its summary rather than back through the wizard
		navigate(company.status === "not_started" ? paths.mode : paths.root);
	};

	return (
		<Page guide="company" width={860} pad="36px 40px 44px">
			<div className="col" style={{ gap: 28 }}>
				<div className="col" style={{ gap: 8 }}>
					<Eyebrow size="lg">{t("company.eyebrow")}</Eyebrow>
					<h2 className="title" style={{ fontSize: 28, letterSpacing: "-.02em" }}>
						{t("company.title")}
					</h2>
					<p style={{ margin: 0, fontSize: 14, color: "var(--muted)" }}>{t("company.body")}</p>
				</div>

				<div className="col" style={{ gap: 14 }} role="radiogroup" aria-label={t("company.title")}>
					{(companies ?? []).map((company) => {
						const blocked = !company.eligible;
						const started = company.status !== "not_started";
						return (
							<ChoiceCard
								key={company.name}
								selected={false}
								disabled={blocked}
								onSelect={() => choose(company)}
								style={{ padding: 20, gap: 12 }}
							>
								<div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
									{!blocked && <Radio on={false} />}
									<div className="col" style={{ gap: 4, flex: 1 }}>
										<div style={{ display: "flex", alignItems: "center", gap: 10 }}>
											<div style={{ fontSize: 17, fontWeight: 600 }}>{company.name}</div>
											{blocked && <Chip tone="outline">{t("company.unavailable")}</Chip>}
											{!blocked && started && (
												<Chip tone="brand">{t(`company.status.${company.status}` as MessageKey)}</Chip>
											)}
										</div>
										{company.defaultTin && (
											<div className="mono" style={{ fontSize: 12, color: "var(--muted-2)" }}>
												{company.defaultTin}
											</div>
										)}
									</div>
								</div>

								{blocked && (
									<>
										<Rule />
										<div className="col" style={{ gap: 5 }}>
											{company.blockers.map((blocker) => (
												<div
													key={blocker.key}
													style={{ fontSize: 12.5, color: "var(--danger)", lineHeight: 1.45 }}
												>
													{t(blocker.key as MessageKey, blocker.params)}
												</div>
											))}
										</div>
									</>
								)}
							</ChoiceCard>
						);
					})}
				</div>

				{companies?.every((c) => !c.eligible) && (
					<div style={{ fontSize: 13, color: "var(--danger)" }}>{t("company.noneEligible")}</div>
				)}

				<div className="actions" style={{ marginTop: "auto" }}>
					<Btn variant="ghost" onClick={() => navigate(paths.welcome)}>
						{t("common.back")}
					</Btn>
				</div>
			</div>
		</Page>
	);
}
