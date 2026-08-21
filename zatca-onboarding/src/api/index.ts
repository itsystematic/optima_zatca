/**
 * The application's entire view of the backend.
 *
 * Everything above this file — hooks, routes, components — imports only from
 * here, and only ever sees the shapes in `./types`.
 *
 * Two implementations sit behind it:
 *
 *   live  `./live`          the real `optima_zatca.api.onboarding.*` methods (default)
 *   mock  `./mock/handlers` an in-memory stand-in, no network at all
 *
 * The choice is made once, at build time, by `./backend` — which Vite resolves
 * to one or the other. Nothing here branches on it, so a production build has no
 * trace of the stand-in: no scenario engine, no fixtures, no dev toolbar.
 *
 * The mock is not decoration: the unit and end-to-end suites run against it, so
 * the whole interface can be exercised without a bench, and it doubles as the
 * specification the real endpoints have to keep satisfying. Select it with
 * `VITE_OZ_API=mock`, which is what `npm test` does.
 *
 * Its scenario controls are deliberately absent from this file — they have no
 * server counterpart, so anything importing them would pull the mock in too.
 * `@/components/DevToolbar` reaches for them directly instead.
 */

import * as backend from "@/api/backend";
import type {
	City,
	Company,
	Guidance,
	PhaseOption,
	LogEntry,
	OtpEntry,
	RegisterInput,
	SaveEntityInput,
	SaveModeInput,
	SaveScopeInput,
	Setup,
	SubmitOtpInput,
} from "./types";

export * from "./types";
export { call } from "./transport";

/**
 * `true` when this build talks to the in-memory stand-in rather than a bench.
 *
 * Vite substitutes the env value at build time, so in a production build this is
 * the literal `false` and the branches behind it are dropped.
 */
export const USING_MOCK = import.meta.env.VITE_OZ_API === "mock";

/* ── Reads ──────────────────────────────────────────────────────────────── */

export const getSetup = (): Promise<Setup> => backend.getSetup();
export const getGuidance = (): Promise<Guidance> => backend.getGuidance();
export const getCompanies = (): Promise<Company[]> => backend.getCompanies();
export const getCities = (): Promise<City[]> => backend.getCities();
export const getPhaseOptions = (): Promise<PhaseOption[]> => backend.getPhaseOptions();

/* ── Wizard decisions ───────────────────────────────────────────────────── */

export const saveMode = (input: SaveModeInput): Promise<Setup> => backend.saveMode(input);
export const saveScope = (input: SaveScopeInput): Promise<Setup> => backend.saveScope(input);
export const saveEntity = (input: SaveEntityInput): Promise<Setup> => backend.saveEntity(input);
export const markEntityVerified = (): Promise<Setup> => backend.markEntityVerified();

/* ── Registers ──────────────────────────────────────────────────────────── */

export const addRegister = (input: RegisterInput): Promise<Setup> => backend.addRegister(input);
export const updateRegister = (id: string, input: RegisterInput): Promise<Setup> =>
	backend.updateRegister(id, input);
export const removeRegister = (id: string): Promise<Setup> => backend.removeRegister(id);
export const setAcknowledged = (value: boolean): Promise<Setup> => backend.setAcknowledged(value);

/* ── The run ────────────────────────────────────────────────────────────── */

export const submitOtp = (input: SubmitOtpInput): Promise<Setup> => backend.submitOtp(input);
export const retryRegisters = (ids: string[], entries: OtpEntry[] = []): Promise<Setup> =>
	backend.retryRegisters(ids, entries);
export const finishWithLive = (): Promise<Setup> => backend.finishWithLive();

/** The exchanges recorded for one register, most recent first. */
export const getRegisterLog = (register: string, limit?: number): Promise<LogEntry[]> =>
	backend.getRegisterLog(register, limit);

/**
 * Point the session at a different company's setup. Everything read afterwards
 * belongs to that company, so the caller has to discard what it is holding.
 */
export const setCompanyScope = (company: string | null): void =>
	backend.setCompanyScope(company);

/** Which company that is, or nothing when the server's default still stands. */
export const scopedCompany = (): string | undefined => backend.scopedCompany();
