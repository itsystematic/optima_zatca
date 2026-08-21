import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { USING_MOCK } from "@/api";
import type { Setup } from "@/api";
// straight at the stand-in, not through `@/api` — see the note there. This file
// is the only thing that imports it, and a production build drops the pair.
import * as mock from "@/api/mock/handlers";
import type { ScenarioName } from "@/api/mock/handlers";
import { qk } from "@/queries/keys";
import { useI18n } from "@/i18n/core";

/**
 * Development-only controls for the mock backend.
 *
 * These have no server counterpart — they exist so every state the design covers
 * (an empty form, a half-filled branch list, a run in flight, a partial failure)
 * can be reached through the real code paths rather than a static gallery.
 * Shown when Vite is in dev mode, or on any build with `?dev=1`.
 */

const SCENARIOS: { value: ScenarioName; label: string }[] = [
	{ value: "fresh", label: "Nothing started" },
	{ value: "single_draft", label: "Single register, drafted" },
	{ value: "multi_draft", label: "3 of 5 registers added" },
	{ value: "ready_to_review", label: "5 registers, at review" },
	{ value: "awaiting_otp", label: "Acknowledged, awaiting OTP" },
	{ value: "running", label: "Run in flight" },
	{ value: "partial_failure", label: "Finished with 1 failure" },
	{ value: "live", label: "Live" },
];

/**
 * The toolbar drives the in-memory backend directly, so it only exists when that
 * backend is the one in use. Against a real bench there is nothing for it to do.
 */
export function isDevToolbarEnabled(): boolean {
	if (!USING_MOCK) return false;
	if (import.meta.env.DEV) return true;
	if (typeof window === "undefined") return false;
	return new URLSearchParams(window.location.search).get("dev") === "1";
}

/**
 * `?scenario=partial_failure` puts the mock into a named state on load, so any
 * screen in the flow can be linked to directly for review or capture.
 */
function useScenarioDeepLink(apply: (name: ScenarioName) => void) {
	const done = useRef(false);
	useEffect(() => {
		if (done.current) return;
		const requested = new URLSearchParams(window.location.search).get("scenario");
		if (!requested) return;
		if (!SCENARIOS.some((s) => s.value === requested)) return;
		done.current = true;
		apply(requested as ScenarioName);
	}, [apply]);
}

/** Only the toolbar applies scenarios, so the mutation lives with it. */
function useApplyScenario() {
	const qc = useQueryClient();
	return useMutation<Setup, Error, ScenarioName>({
		mutationFn: mock.applyScenario,
		onSuccess: (setup) => qc.setQueryData(qk.setup, setup),
	});
}

export function DevToolbar() {
	const qc = useQueryClient();
	const { lang, setLang } = useI18n();
	const applyScenario = useApplyScenario();
	const [dev, setDev] = useState(() => mock.readDevState());

	useScenarioDeepLink((name) => applyScenario.mutate(name));

	const update = async (change: () => Promise<unknown>) => {
		await change();
		setDev(mock.readDevState());
		await qc.invalidateQueries({ queryKey: qk.setup });
	};

	return (
		<div className="devbar">
			<span className="devbar__tag">Mock backend</span>

			<div className="devbar__group">
				<span className="devbar__label">Scenario</span>
				<select
					defaultValue=""
					onChange={(e) => {
						const value = e.target.value as ScenarioName;
						if (value) applyScenario.mutate(value);
						e.target.value = "";
					}}
				>
					<option value="">Jump to…</option>
					{SCENARIOS.map((s) => (
						<option key={s.value} value={s.value}>
							{s.label}
						</option>
					))}
				</select>
			</div>

			<div className="devbar__group">
				<span className="devbar__label">Pace</span>
				<button
					type="button"
					aria-pressed={dev.speed === 1}
					onClick={() => update(() => mock.setSpeed(1))}
				>
					demo
				</button>
				<button
					type="button"
					aria-pressed={dev.speed === 4}
					onClick={() => update(() => mock.setSpeed(4))}
				>
					lifelike
				</button>
			</div>

			<div className="devbar__group">
				<span className="devbar__label">Next run</span>
				<button
					type="button"
					aria-pressed={dev.failureMode === "none"}
					onClick={() => update(() => mock.setFailureMode("none"))}
				>
					all succeed
				</button>
				<button
					type="button"
					aria-pressed={dev.failureMode === "one_otp_expired"}
					onClick={() => update(() => mock.setFailureMode("one_otp_expired"))}
				>
					one OTP expired
				</button>
			</div>

			<div className="devbar__group">
				<span className="devbar__label">Lang</span>
				<button type="button" aria-pressed={lang === "en"} onClick={() => setLang("en")}>
					en
				</button>
				<button type="button" aria-pressed={lang === "ar"} onClick={() => setLang("ar")}>
					ar
				</button>
			</div>

			<div className="devbar__spacer" />
			<span className="devbar__note">
				State persists in localStorage · no network calls are made
			</span>
		</div>
	);
}
