import { call } from "./transport";
import { scopedCompany, setCompanyScope } from "./scope";
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

export { scopedCompany, setCompanyScope };

/**
 * The real backend: `optima_zatca.api.onboarding.*`.
 *
 * Arguments are flat keyword arguments, which is how Frappe delivers them, and
 * every mutation answers with the whole `Setup` so the query cache can be primed
 * from the response instead of refetching.
 *
 * `company` is optional everywhere. Omitted, the server uses the session's
 * default company, or the only one if the site has exactly one; with several and
 * no default it fails with `api.chooseCompany`.
 */

const method = (name: string) => `optima_zatca.api.onboarding.${name}`;

const scope = () => ({ company: scopedCompany() });

export const getSetup = () => call<Setup>(method("get_setup"), scope());
export const getGuidance = () => call<Guidance>(method("get_guidance"), scope());
export const getCompanies = () => call<Company[]>(method("get_companies"));
export const getCities = () => call<City[]>(method("get_cities"));
export const getPhaseOptions = () => call<PhaseOption[]>(method("get_phase_options"), scope());

export const saveMode = (input: SaveModeInput) =>
	call<Setup>(method("save_mode"), { ...scope(), ...input });
export const saveScope = (input: SaveScopeInput) =>
	call<Setup>(method("save_scope"), { ...scope(), ...input });
// the entity form names the company itself, so its choice wins over the scope
export const saveEntity = (input: SaveEntityInput) =>
	call<Setup>(method("save_entity"), { ...scope(), ...input });
export const markEntityVerified = () =>
	call<Setup>(method("mark_entity_verified"), scope());

export const addRegister = (input: RegisterInput) =>
	call<Setup>(method("add_register"), { ...scope(), ...input });
export const updateRegister = (id: string, input: RegisterInput) =>
	call<Setup>(method("update_register"), { ...scope(), id, ...input });
export const removeRegister = (id: string) =>
	call<Setup>(method("remove_register"), { ...scope(), id });
export const setAcknowledged = (value: boolean) =>
	call<Setup>(method("set_acknowledged"), { ...scope(), value });

export const submitOtp = (input: SubmitOtpInput) =>
	call<Setup>(method("submit_otp"), { ...scope(), entries: input.entries });

/**
 * Retry the registers that failed.
 *
 * A register that already holds a compliance certificate resumes without a fresh
 * code; one that failed earlier than that needs one, and the server refuses
 * without it. The caller decides which by looking at the compliance stage.
 */
export const retryRegisters = (ids: string[], entries: OtpEntry[] = []) =>
	call<Setup>(method("retry_registers"), { ...scope(), ids, entries });

export const finishWithLive = () => call<Setup>(method("finish_with_live"), scope());

/**
 * The exchanges recorded for one register, most recent first.
 *
 * Not scoped by company: a register names itself, and the server resolves the
 * company from it.
 */
export const getRegisterLog = (register: string, limit?: number) =>
	call<LogEntry[]>(method("get_register_log"), { register, limit });
