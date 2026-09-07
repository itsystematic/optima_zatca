import type { StageState } from "@/api";
import { cx } from "./primitives";

/**
 * The five-link chain — keys, CSR, compliance cert, test invoices, production
 * cert. Exactly one link may be `run`, and only that one carries motion.
 */
export function StageBar({
	stages,
	runPct = 0,
	slim = false,
}: {
	stages: StageState[];
	runPct?: number;
	slim?: boolean;
}) {
	return (
		<div className={cx("stages", slim && "stages--slim")}>
			{stages.map((s, i) => (
				<div key={i} className={cx("stage", s !== "idle" && `stage--${s}`)}>
					{s === "run" && <div className="stage__fill" style={{ width: `${runPct}%` }} />}
				</div>
			))}
		</div>
	);
}
