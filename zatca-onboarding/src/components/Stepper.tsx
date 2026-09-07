import { cx, Mark } from "./primitives";

export type Step = {
	badge: string;
	label: string;
	sub?: string;
	state: "done" | "current" | "idle";
};

/**
 * The four-step wizard header. `size` matches the two variants in the design —
 * 30px badges on step 1, 28px once a step has been banked.
 */
export function Stepper({ steps, size = "lg" }: { steps: Step[]; size?: "lg" | "md" }) {
	const badge = size === "lg" ? 30 : 28;
	const badgeFont = size === "lg" ? 13 : 12.5;
	const gap = size === "lg" ? 12 : 11;

	return (
		<div className="card stepper" style={{ padding: size === "lg" ? "20px 26px" : "18px 26px" }}>
			{steps.map((s, i) => (
				<Fragmentish key={s.badge}>
					<div
						className={cx("stepper__step", i < steps.length - 1 && "stepper__step--grow")}
						style={{ gap }}
					>
						{s.state === "done" ? (
							<Mark
								kind="tick"
								size={badge}
								font={13}
								style={{ borderRadius: "var(--r-lg)", fontFamily: "var(--font-sans)" }}
							/>
						) : (
							<span
								className={cx("stepper__badge", s.state === "current" && "stepper__badge--current")}
								style={{ width: badge, height: badge, fontSize: badgeFont }}
							>
								{s.badge}
							</span>
						)}
						<div className="col">
							<div
								className={cx(
									"stepper__title",
									(s.state === "current" || s.state === "done") && "stepper__title--active",
								)}
								style={{ fontSize: size === "lg" ? 13.5 : 13, fontWeight: s.state === "done" ? 500 : undefined }}
							>
								{s.label}
							</div>
							{s.sub && (
								<div className={cx("stepper__state", s.state === "current" && "stepper__state--active")}>
									{s.sub}
								</div>
							)}
						</div>
					</div>
					{i < steps.length - 1 && <div className="stepper__link" />}
				</Fragmentish>
			))}
		</div>
	);
}

// Keyed fragment helper so the map above stays readable.
function Fragmentish({ children }: { children: React.ReactNode }) {
	return <>{children}</>;
}
