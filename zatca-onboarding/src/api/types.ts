/**
 * The wire contract between the UI and the e-invoicing backend.
 *
 * These types describe what the server sends and accepts. They are deliberately
 * free of UI concerns — no colours, no labels, no React — so that when the mock
 * in `api/mock/` is replaced by real Frappe endpoints, nothing above this file
 * has to change.
 */

/**
 * Which authority endpoint a registration talks to.
 *
 * These are not interchangeable: a certificate issued in one is refused by the
 * others, and an invoice sent anywhere but production has no legal effect.
 */
export type Environment = "sandbox" | "simulation" | "production";

/** Where the company is in the registration lifecycle. */
export type SetupStatus =
	| "not_started"
	/** decisions and registers are being entered; nothing submitted */
	| "draft"
	/** submitted; certificates are being issued right now */
	| "running"
	/** the run finished with at least one register failed */
	| "partial"
	/** every register holds a production certificate */
	| "live";

/** The wizard step the setup is currently parked on. */
export type SetupStep =
	| "mode"
	| "scope"
	| "entity"
	| "registers"
	| "review"
	| "otp"
	| "progress"
	| "done";

/** Which obligation the company is registering for. */
export type Phase = "phase_1" | "phase_2";

/** How many commercial registers are in play. */
export type Scope = "single" | "multiple";

/** The five links of the certificate chain, in order. */
export const STAGE_KEYS = ["keys", "csr", "compliance", "tests", "production"] as const;
export type StageKey = (typeof STAGE_KEYS)[number];

export type StageState = "idle" | "run" | "done" | "fail";

/** Per-register lifecycle, independent of every other register. */
export type RegisterStatus = "draft" | "queued" | "running" | "live" | "failed";

export type Address = {
	buildingNumber: string;
	street: string;
	district: string;
	city: string;
	postalCode: string;
	/** locked to the mandate's country; the server owns this value */
	country: string;
	additionalNumber: string;
	vatGroupNumber: string;
};

export type Register = {
	id: string;
	/** 1-based position, as shown in the review table */
	index: number;
	/**
	 * The authority this register is certified against. `null` while the server
	 * does not report it — never assumed, because guessing "production" would
	 * tell someone their invoices count when they do not.
	 */
	environment: Environment | null;
	registerName: string;
	crn: string;
	address: Address;
	status: RegisterStatus;
	/** null until the register has been submitted at least once */
	run: RegisterRun | null;
	certificate: Certificate | null;
};

/**
 * Where one register stands. Deliberately structured rather than prose: the
 * server reports which stage is moving, and the UI writes the sentence — so the
 * status column translates without the backend knowing a language.
 */
export type RegisterRun = {
	stages: Record<StageKey, StageState>;
	/** 0–100 through the one stage that is currently `run`, else 0 */
	stageProgress: number;
	/** the stage this row is reporting on */
	stage: StageKey;
	/** 1-based position of that stage in the chain */
	stageIndex: number;
	/** which of the six test documents is in flight, during that stage only */
	testInvoice?: number;
	/** wall-clock seconds this register has been working */
	elapsedSeconds: number;
	error: RunError | null;
};

export type Certificate = {
	fingerprint: string;
	/** both dates are absent until the authority states them */
	issuedAt: string | null;
	validTo: string | null;
};

/** A failure the authority returned, in the shape the detail panel renders. */
export type RunError = {
	/** the authority's error code; the UI looks up `error.<code>.*` for copy */
	code: string;
	httpStatus: number;
	endpoint: string;
	requestId: string;
	attempt: number;
	maxAttempts: number;
	occurredAt: string;
	/** extra key/value lines for the technical block */
	details: Record<string, string>;
};

export type LegalEntity = {
	company: string;
	legalNameAr: string;
	tin: string;
};

export type Setup = {
	id: string;
	company: string;
	/** The authority these registrations are made against; see `Environment`. */
	environment: Environment | null;
	status: SetupStatus;
	step: SetupStep;
	phase: Phase | null;
	scope: Scope | null;
	entity: LegalEntity | null;
	entityVerifiedOn: string | null;
	/** how many registers the operator said to expect, for the "3 of 5" rail */
	expectedRegisters: number | null;
	registers: Register[];
	acknowledged: boolean;
	/** support reference, minted when the run starts */
	reference: string | null;
	startedAt: string | null;
	completedAt: string | null;
	modified: string;
};

/**
 * Something the server checked, or something it cannot check.
 *
 * A **blocker** is a condition this system tested and found wanting: it disables
 * the choice and names a fix. A **note** is a condition it has no way to verify —
 * whether a taxpayer has been called up for an obligation is the authority's to
 * decide and is communicated to them directly — so it is stated as something to
 * confirm rather than presented as though it had been checked.
 */
export type Finding = { key: string; params?: MessageParams };

/** Reference data the wizard needs but does not own. */
export type Company = {
	name: string;
	/** true when VAT settings and a print format are already linked */
	linked: boolean;
	defaultTin: string;
	defaultLegalNameAr: string;
	/**
	 * Whether this company can be registered at all, decided before the wizard
	 * starts rather than three screens in. Learning that a company is unsupported
	 * after its obligation and scope have been answered means answering them
	 * again for a company that was never going to work.
	 */
	eligible: boolean;
	blockers: Finding[];
	/** where this company's own setup stands, so the picker can say "in progress" */
	status: SetupStatus;
};

export type City = { name: string };

/** What the explainer page renders. Server-owned so copy can change per country. */
export type LifecycleStep = { key: string; title: string; body: string; actor: string };
export type ChecklistItem = { key: string; title: string; body: string };

export type Guidance = {
	lifecycle: LifecycleStep[];
	checklist: ChecklistItem[];
	portalUrl: string;
	otpTtlMinutes: number;
};

/** What the authority was asked, and what it said back. */
export type LogOutcome = "ok" | "rejected" | "error" | "timeout";

/**
 * One exchange with the authority.
 *
 * The diagnostic record behind a register: during verification each of the six
 * compliance documents is a separate call with its own timing and outcome, which
 * is exactly what has to be answerable when one of them is refused.
 */
export type LogEntry = {
	id: string;
	at: string;
	environment: Environment;
	/** what was attempted, e.g. "compliance document", "report invoice" */
	operation: string;
	outcome: LogOutcome;
	httpStatus: number | null;
	durationMs: number | null;
	/** the authority's own words, present only when it refused */
	message: string | null;
};


/** Whether this company may register for one obligation, and on what grounds. */
export type PhaseOption = {
	phase: Phase;
	eligible: boolean;
	blockers: Finding[];
	notes: Finding[];
	recommended: boolean;
	/** never present without `recommended`; the fact that justified it */
	recommendedBecause?: string | null;
};

/** One OTP the operator is entering, keyed by register. */
export type OtpEntry = { registerId: string; code: string };

/** Values interpolated into a translated message. */
export type MessageParams = Record<string, string | number>;

/** A rule failure, named by message key so it can be rendered in any language. */
export type Problem = { key: string; params?: MessageParams } | null;

/**
 * A field-level failure from the server. Mirrors what a Frappe whitelisted
 * method would raise, so client and server validation render identically.
 */
export type FieldError = { field: string; key: string; params?: MessageParams };

export class ApiError extends Error {
	readonly fieldErrors: FieldError[];
	readonly status: number;
	/** message key for the UI; `message` stays as an untranslated fallback */
	readonly key: string;

	constructor(key: string, opts: { fieldErrors?: FieldError[]; status?: number } = {}) {
		super(key);
		this.name = "ApiError";
		this.key = key;
		this.fieldErrors = opts.fieldErrors ?? [];
		this.status = opts.status ?? 400;
	}
}

/* ── Request payloads ───────────────────────────────────────────────────── */

export type SaveEntityInput = LegalEntity;
export type SaveModeInput = { phase: Phase };
export type SaveScopeInput = { scope: Scope; expectedRegisters?: number };
export type RegisterInput = {
	registerName: string;
	crn: string;
	address: Partial<Address>;
};
export type SubmitOtpInput = { entries: OtpEntry[] };
