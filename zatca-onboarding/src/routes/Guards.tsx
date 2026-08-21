import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import type { SetupStep } from "@/api";
import { useT } from "@/i18n/core";
import { useCompanies, useSetup } from "@/queries/setup";
import { USING_MOCK, scopedCompany } from "@/api";
import { canReach, effectiveStep, stepPath, paths } from "./paths";

/** The desk chrome, greyed, while the setup record is in flight. */
export function SetupLoading() {
	return (
		<div className="loading">
			<div className="skeleton loading__bar" />
			<div className="skeleton loading__body" />
		</div>
	);
}

/**
 * Keeps the wizard honest: a step the operator has not earned redirects to the
 * furthest one they have. This is what makes a bookmarked or pasted URL resume
 * correctly instead of rendering a half-built form.
 */
export function RequireStep({ step, children }: { step: SetupStep; children: ReactNode }) {
	const { data: setup, isLoading, isError, error } = useSetup();
	const { data: companies } = useCompanies();

	// With several companies and none chosen, the wizard would silently operate on
	// whichever one the session defaults to — and the operator would find out two
	// screens later, on a record that is not the one they meant.
	const mustChoose =
		!USING_MOCK && !scopedCompany() && (companies?.length ?? 0) > 1 && step !== "mode";
	if (mustChoose) return <Navigate to={paths.company} replace />;

	if (isLoading) return <SetupLoading />;
	if (isError) return <LoadFailed message={error instanceof Error ? error.message : undefined} />;
	if (!setup) return <SetupLoading />;

	if (!canReach(step, setup)) {
		return <Navigate to={stepPath[effectiveStep(setup)]} replace />;
	}


	return <>{children}</>;
}

/** `/` sends people wherever they actually are. */
export function ResumeRedirect() {
	const { data: setup, isLoading } = useSetup();
	if (isLoading || !setup) return <SetupLoading />;
	if (setup.status === "not_started") return <Navigate to={paths.welcome} replace />;
	return <Navigate to={stepPath[effectiveStep(setup)]} replace />;
}

function LoadFailed({ message }: { message?: string }) {
	const t = useT();
	return (
		<div className="stub">
			<div className="stub__card">
				<h1 className="stub__title">{t("guard.failed.title")}</h1>
				<p className="stub__body">
					{t("guard.failed.body", { reason: message ?? t("guard.failed.reason") })}
				</p>
			</div>
		</div>
	);
}
