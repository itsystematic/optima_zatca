import { useState } from "react";
import { Link } from "react-router-dom";
import type { Register } from "@/api";
import { EnvironmentMarker } from "@/components/Environment";
import { Page } from "@/components/Page";
import { RegisterLog } from "@/components/RegisterLog";
import { Eyebrow, cx } from "@/components/primitives";
import { useT } from "@/i18n/core";
import { useSetup } from "@/queries/setup";
import { paths } from "./paths";

/**
 * The diagnostic surface.
 *
 * One register at a time, because the question people arrive with is about a
 * particular one — "the Jeddah branch failed, what did the authority say".
 */
export function Log() {
	const t = useT();
	const { data: setup } = useSetup();
	const registers = setup?.registers ?? [];
	const [selectedId, setSelectedId] = useState<string | null>(null);

	const selected: Register | null =
		registers.find((r) => r.id === selectedId) ?? registers[0] ?? null;

	return (
		<Page width={1040}>
			<div className="col" style={{ gap: 20 }}>
				<div className="col" style={{ gap: 7 }}>
					<Eyebrow size="lg">{t("log.title")}</Eyebrow>
					<h2 className="title" style={{ fontSize: 26, letterSpacing: "-.02em" }}>
						{t("log.subtitle")}
					</h2>
				</div>

				{registers.length === 0 ? (
					<div className="card">
						<div className="log__empty">
							{t("log.emptyRegisters")}{" "}
							<Link to={paths.root} style={{ fontWeight: 600 }}>
								{t("log.backToSetup")}
							</Link>
						</div>
					</div>
				) : (
					<div
						style={{
							display: "grid",
							gridTemplateColumns: registers.length > 1 ? "280px 1fr" : "1fr",
							gap: 20,
							alignItems: "start",
						}}
					>
						{registers.length > 1 && (
							<div className="card col" style={{ overflow: "hidden" }}>
								<div
									className="eyebrow"
									style={{
										padding: "12px 16px",
										background: "var(--surface-2)",
										borderBottom: "1px solid var(--line)",
									}}
								>
									{t("log.register")}
								</div>
								{registers.map((r) => (
									<button
										key={r.id}
										type="button"
										onClick={() => setSelectedId(r.id)}
										aria-pressed={r.id === selected?.id}
										className={cx("logpick", r.id === selected?.id && "logpick--on")}
									>
										<span style={{ fontSize: 13, fontWeight: 600 }}>{r.registerName}</span>
										<span className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
											{r.crn}
										</span>
									</button>
								))}
							</div>
						)}

						<div className="card col" style={{ overflow: "hidden" }}>
							{selected && (
								<div
									className="row"
									style={{
										gap: 12,
										padding: "14px 16px",
										borderBottom: "1px solid var(--line)",
									}}
								>
									<div className="col" style={{ gap: 2, flex: 1 }}>
										<div style={{ fontSize: 14, fontWeight: 600 }}>{selected.registerName}</div>
										<div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
											{selected.crn}
										</div>
									</div>
									<EnvironmentMarker environment={selected.environment ?? setup?.environment ?? null} />
								</div>
							)}
							<RegisterLog register={selected} />
						</div>
					</div>
				)}
			</div>
		</Page>
	);
}
