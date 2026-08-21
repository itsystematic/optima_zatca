import type { Message } from "./types";

/**
 * The canonical message catalogue.
 *
 * Every user-visible string in the app lives here. `*asterisks*` mark emphasis
 * and `` `backticks` `` mark a literal value or menu path, so a translator can
 * move that emphasis to wherever the sentence needs it.
 */
export const en = {
	/* ── Shared ─────────────────────────────────────────────────────────── */
	"common.continue": "Continue",
	"common.back": "Back",
	"common.close": "Close",
	"common.cancel": "Cancel",
	"common.edit": "Edit",
	"common.remove": "Remove",
	"common.delete": "Delete",
	"common.discard": "Discard",
	"common.required": "Required",
	"common.optional": "optional",
	"common.optionalValue": "Optional",
	"common.locked": "LOCKED",
	"common.live": "Live",
	"common.viewLog": "View log",
	"common.language": "Language",
	"common.somethingWrong": "Something went wrong. Try again.",

	/* ── 01 Welcome ─────────────────────────────────────────────────────── */
	"welcome.eyebrow": "E-Invoicing compliance · setup wizard",
	"welcome.title": "Register this company for e-invoicing in one sitting.",
	"welcome.body":
		"We generate your cryptographic key pair, obtain your compliance certificate, pass the mandatory test invoices and switch you to a live production certificate. No consultant, no support ticket.",
	"welcome.start": "Start setup",
	"welcome.resume": "Resume setup",
	"welcome.view": "View your registration",
	"welcome.howItWorks": "How it works",
	"welcome.meta.duration": "~12 min",
	"welcome.meta.otp": "one OTP per commercial register",
	"welcome.meta.reversible": "reversible until you submit",
	"welcome.authorities.label": "Issued and verified against",
	"welcome.authorities.tax": "Tax Authority",
	"welcome.authorities.commerce": "Ministry of Commerce",
	"welcome.authorities.ca": "Certificate Authority",

	/* ── 02 How it works ────────────────────────────────────────────────── */
	"howItWorks.eyebrow": "The registration lifecycle",
	"howItWorks.title": "What happens, in this order — and most of it without you.",
	"howItWorks.checklist": "What you'll need before starting",
	"howItWorks.otp.label": "About the OTP",
	"howItWorks.otp.body":
		"Each commercial register gets its own one-time password, generated in the tax portal under `Onboarding → Generate OTP`. Codes expire {minutes} minutes after they are issued, so generate them right before you reach step 4.",
	"howItWorks.otp.link": "Open the tax portal ↗",
	"howItWorks.key.title": "Your private key never leaves this server",
	"howItWorks.key.body":
		"Keys are generated locally; only the signing request travels to the authority.",
	"howItWorks.resume.title": "Stop and resume anytime",
	"howItWorks.resume.body": "Progress is saved per register until certificates are issued.",

	"lifecycle.keys.title": "A key pair is generated",
	"lifecycle.keys.body":
		"A private key is created and never leaves this server. Every invoice you issue will be signed with it.",
	"lifecycle.csr.title": "A certificate is requested",
	"lifecycle.csr.body":
		"The request carries your commercial register, tax number and address, and is submitted with the one-time password from the portal.",
	"lifecycle.compliance.title": "A compliance certificate is issued",
	"lifecycle.compliance.body":
		"This certificate proves the system works. It cannot yet be used for real invoices.",
	"lifecycle.tests.title": "Six documents are checked",
	"lifecycle.tests.body":
		"One of every document type you can issue is signed and submitted, so the authority can confirm they are valid before trusting real ones.",
	"lifecycle.production.title": "The production certificate arrives",
	"lifecycle.production.body":
		"From this point your invoices are cleared or reported for real, and each one carries a QR code a buyer can verify.",
	"lifecycle.actor.system": "this system",
	"lifecycle.actor.authority": "the authority",

	"checklist.tin.title": "Your 15-digit tax number",
	"checklist.tin.body":
		"It begins and ends with 3. Check it on the authority's taxpayer lookup before you start.",
	"checklist.registers.title": "Every commercial register number",
	"checklist.registers.body":
		"Ten digits each. One certificate is issued per register, so have them all to hand.",
	"checklist.address.title": "The national address of each register",
	"checklist.address.body":
		"Building number, street, district, city and postal code. The building number is four digits and the postal code five.",
	"checklist.arabic.title": "Your legal name in Arabic",
	"checklist.arabic.body":
		"Exactly as registered. It is printed on every invoice and embedded in the certificate.",
	"checklist.otp.title": "A one-time password per register",
	"checklist.otp.body":
		"Generated on the portal. Each is valid for one hour and can be used once, so generate them when you reach the last step.",

	/* ── 03 Mode ────────────────────────────────────────────────────────── */
	"mode.eyebrow": "Setup · 1 of 4 decisions",
	"mode.title": "Which obligation are you registering for?",
	"mode.body":
		"Your tax authority letter states the phase and your enforcement date. You can move up later; you cannot move back.",
	"mode.unlocks": "What this unlocks",
	"mode.recommended": "Recommended for you",
	"mode.selected": "Selected: {mode}",
	"mode.phase1.title": "Phase 1 — Generation",
	"mode.phase1.tag": "QR-code invoices, no live connection",
	"mode.phase1.u1":
		"Every printed and PDF invoice carries a compliant QR code with the hashed totals",
	"mode.phase1.u2": "Tamper-evident local archive with invoice hash chaining",
	"mode.phase1.u3": "Arabic + English bilingual invoice print format",
	"mode.phase1.foot": "*Not included:* clearance, reporting, cryptographic stamps.",
	"mode.phase1.mono": "no certificates issued",
	"mode.phase2.title": "Phase 2 — Integration",
	"mode.phase2.tag": "Full clearance and reporting, live connection",
	"mode.phase2.u1":
		"B2B invoices cleared by the authority *before* you send them to the customer",
	"mode.phase2.u2": "B2C invoices reported automatically within 24 hours",
	"mode.phase2.u3":
		"Cryptographic stamp and UUID on every document, with per-invoice status in the log",
	"mode.phase2.u4": "Everything in Phase 1, including the QR code",
	"mode.phase2.mono": "compliance + production certificates issued",

	/* ── 04 Scope ───────────────────────────────────────────────────────── */
	"scope.eyebrow": "Setup · 2 of 4 decisions",
	"scope.title": "How many commercial registers are you registering?",
	"scope.body":
		"One certificate is issued per register. Branches that invoice under the same register count as one.",
	"scope.downstream": "What changes downstream",
	"scope.single.title": "Single registration",
	"scope.single.tag": "One register, one certificate",
	"scope.single.preview": "1 register",
	"scope.single.body":
		"Step 2 asks for one register and address. Step 4 asks for a single OTP. Registration finishes in about two minutes.",
	"scope.multiple.title": "Multiple branches or registers",
	"scope.multiple.tag": "One certificate per register, issued in parallel",
	"scope.multiple.previewUnknown": "n registers",
	"scope.multiple.preview": { one: "{count} register", other: "{count} registers" },
	"scope.multiple.body":
		"Step 2 becomes a repeatable form with a branch list. Step 4 asks for *one OTP per register*. Registration runs branch by branch, and one failure does not block the rest.",
	"scope.expected.label": "How many do you expect?",
	"scope.expected.hint": "Tracks progress in step 2. You can add more later.",
	"scope.expected.range": "Between 2 and 99.",

	/* ── Wizard steps ───────────────────────────────────────────────────── */
	"steps.entity": "Legal entity",
	"steps.registers": "Registers & address",
	"steps.review": "Review",
	"steps.register": "Register",
	"steps.inProgress": "In progress",
	"steps.next": "Next",

	/* ── 05 Legal entity ────────────────────────────────────────────────── */
	"entity.title": "Legal entity details",
	"entity.body":
		"These values are stamped into every certificate. They must match the tax portal character for character.",
	"entity.company.label": "Company",
	"entity.company.placeholder": "Choose a company",
	"entity.company.linked": "Linked to VAT settings and the invoice print format.",
	"entity.company.switches":
		"Linked to VAT settings and the invoice print format. Each company is registered separately — choosing another opens its own setup.",
	"entity.company.unlinked":
		"This company has no VAT settings linked yet. Registration will still work, but the print format will not carry the QR code until you link it.",
	"entity.arabic.label": "Legal name in Arabic",
	"entity.arabic.placeholder": "الاسم القانوني بالعربية",
	"entity.arabic.hint": "Exactly as registered, including any suffix.",
	"entity.arabic.valid": "Arabic script detected · matches the register on file",
	"entity.tin.label": "Tax identification number",
	"entity.tin.meta": "{count} digits",
	"entity.tin.placeholder": "3XXXXXXXXXXXX3",
	"entity.tin.valid": "Valid format",
	"entity.ready": "Ready to continue",
	"entity.fix": { one: "Fix {count} field to continue", other: "Fix {count} fields to continue" },
	"entity.verify.title": "Verify before you continue",
	"entity.verify.body":
		"A mismatch here is only discovered when the authority rejects your certificate request. Two minutes of checking saves a failed registration.",
	"entity.verify.s1": "Sign in to the tax portal with the company account",
	"entity.verify.s2": "Open `Taxpayer profile → Registration`",
	"entity.verify.s3": "Compare the Arabic legal name and TIN exactly, including spacing",
	"entity.verify.link": "Open the taxpayer profile ↗",
	"entity.verify.never":
		"Last verified for this company: never. We record the date once you confirm.",
	"entity.verify.on": "Verified for this company on {date}.",
	"entity.verify.action": "I've checked the portal",
	"entity.saved": "Saved {when}",

	/* ── 06 / 07 Registers ──────────────────────────────────────────────── */
	"registers.title": "Commercial register",
	"registers.body": "Identify the register first. The address it is filed under unlocks below.",
	"registers.crn.label": "Commercial register number",
	"registers.crn.placeholder": "{count} digits",
	"registers.crn.valid": "Valid format · {count} digits",
	"registers.crn.unused": "Valid format · not yet used in this setup",
	"registers.name.label": "Register name",
	"registers.name.placeholder": "Riyadh — Head office",
	"registers.name.hint": "Shown on the invoice and in the e-invoicing log",
	"registers.unlocked.both": "Unlocked — both fields valid",
	"registers.unlocked.address": "Address unlocked",
	"registers.locked":
		"The registered address unlocks once the register is named and its {count}-digit number is valid.",
	"registers.address.title": "Registered address",
	"registers.address.filedUnder": "As filed under register {crn}",
	"registers.address.note":
		"Building number is the 4-digit value from the national address. Additional number and VAT group number are optional and live under `More options`.",
	"registers.field.building": "Building number",
	"registers.field.street": "Street",
	"registers.field.district": "District",
	"registers.field.city": "City",
	"registers.field.postal": "Postal code",
	"registers.field.country": "Country",
	"registers.field.additional": "Additional number",
	"registers.city.placeholder": "Choose a city",
	"registers.saveContinue": "Save and continue",
	"registers.singleFooter": "Single registration · 1 register",
	"registers.added": "Registers added",
	"registers.ofExpected": "of {count} expected",
	"registers.countOnly": { one: "register", other: "registers" },
	"registers.rowInProgress": "Register {n} — in progress",
	"registers.fillingIn": "Filling in now",
	"registers.addAnother": "+ Add another register",
	"registers.addNote":
		"You can add registers now or after go-live. Each one needs its own OTP.",
	"registers.headingOf": "Register {n} of {total}",
	"registers.heading": "Register {n}",
	"registers.headingEdit": "Editing register {n}",
	"registers.stepLabel": "Step 2 · Registers & address",
	"registers.chipDraft": "Draft · not submitted",
	"registers.chipEditing": "Saved · editing",
	"registers.save": "Save register",
	"registers.saveChanges": "Save changes",
	"registers.saveAdd": "Save and add another",
	"registers.autosaving": "Multiple registers · autosaving",
	"registers.summary.address": "Address",
	"registers.summary.building": "Building no.",
	"registers.summary.mode": "Mode",

	/* ── 08 Review ──────────────────────────────────────────────────────── */
	"review.eyebrow": "Step 3 of 4 · Review",
	"review.title": "Check every register before certificates are issued",
	"review.stat.registers": { one: "register", other: "registers" },
	"review.stat.certificates": { one: "certificate", other: "certificates" },
	"review.stat.otps": { one: "OTP needed", other: "OTPs needed" },
	"review.col.index": "#",
	"review.col.name": "Register name",
	"review.col.crn": "CR number",
	"review.col.city": "City",
	"review.col.address": "Registered address",
	"review.col.mode": "Mode",
	"review.col.actions": "Actions",
	"review.addAnother": "+ Add another register",
	"review.legalEntity": "Legal entity: {company} · TIN {tin}",
	"review.ack":
		"I confirm these details match the company's official records. I understand that certificates are issued in this legal name, that a production certificate cannot be edited after issue, and that invoices issued under an incorrect register may be rejected by the authority.",
	"review.continue": "Continue to OTP entry",
	"review.finish": "Register these details",
	"review.ackFirst": "Confirm the details first",
	"review.next": "Next: one OTP per register, generated in the tax portal",
	"review.nextPhase1":
		"Phase 1 issues no certificates, so there is no code to enter — your invoices start carrying the QR code straight away.",
	"review.phase1": "Phase 1",
	"review.phase2": "Phase 2",

	/* ── 09 OTP ─────────────────────────────────────────────────────────── */
	"otp.title": "Enter one OTP per register",
	"otp.body":
		"Generate the codes in the tax portal now — each one expires {minutes} minutes after it is issued.",
	"otp.where": "Where do I get these?",
	"otp.cr": "CR {crn}",
	"otp.complete": "Complete",
	"otp.waiting": "Waiting for code",
	"otp.confirm": "Confirm and register",
	"otp.entered": "{done} of {total} entered",
	"otp.enterNext": "Enter the {name} code to continue",
	"otp.allEntered": "All codes entered",
	"otp.group": "OTP for {name}",
	"otp.digit": "OTP for {name}, digit {n}",

	/* ── 10 / 11 The run ────────────────────────────────────────────────── */
	"progress.status.running": "registering",
	"progress.status.finished": { one: "finished with {count} failure", other: "finished with {count} failures" },
	"progress.elapsed": "running · {time} elapsed",
	"progress.title": { one: "Registering {count} commercial register", other: "Registering {count} commercial registers" },
	"progress.leave":
		"You can leave this page — registration continues in the background and we email you when it finishes.",
	"progress.complete": "of {total} complete",
	"progress.running": "{count} running",
	"progress.eta": "Estimated 1–3 minutes remaining",
	"progress.col.register": "Register",
	"progress.col.chain": "Keys → CSR → compliance cert → test invoices → production cert",
	"progress.col.status": "Status",
	"progress.independent":
		"Registers are processed independently. A failure on one never affects the others.",
	"progress.fullLog": "Open full technical log",
	// two independent counts, so two messages: one sentence cannot pluralise both
	"progress.settled.live": { one: "{count} register is live.", other: "{count} registers are live." },
	"progress.settled.failed": { one: "{count} needs another attempt.", other: "{count} need another attempt." },
	"progress.settled.body": { one: "The one that succeeded is already issuing cleared invoices. Nothing is lost by retrying the other later.", other: "The {live} that succeeded are already issuing cleared invoices. Nothing is lost by retrying the rest later." },
	"progress.failedCount": "{count} failed",
	"progress.showDetail": "Show detail ▾",
	"progress.hideDetail": "Hide detail ▴",
	"progress.technical": "Technical detail",
	"progress.retryThis": "Retry this register",
	"progress.copyDiagnostics": "Copy diagnostics",
	"progress.newOtp": "Generate a new OTP ↗",
	"progress.continueWith": { one: "Continue with {count} register", other: "Continue with {count} registers" },
	"progress.retryAll": "Retry all failed",
	"progress.draftNote": { one: "{names} stays in draft. You can finish it any time from `Setup → E-Invoicing → Registers`.", other: "{names} stay in draft. You can finish them any time from `Setup → E-Invoicing → Registers`." },

	"run.queued": "Queued",
	"run.queuedDetail": "waiting for a worker",
	"run.stage.keys": "Generating key pair",
	"run.stage.csr": "Submitting signing request",
	"run.stage.compliance": "Requesting compliance certificate",
	"run.stage.tests": "Sending test invoice {n} of 6",
	"run.stage.production": "Issuing production certificate",
	"run.done": "Production certificate issued",
	"run.completedIn": "completed in {time}",
	"run.stageOf": "stage {n} of {total} · {time}",
	"run.failedAt.keys": "Failed at key generation",
	"run.failedAt.csr": "Failed at signing request",
	"run.failedAt.compliance": "Failed at compliance certificate",
	"run.failedAt.tests": "Failed at test invoices",
	"run.failedAt.production": "Failed at production certificate",

	"error.otp_expired.summary": "The OTP for this register had already expired.",
	"error.otp_expired.remedy":
		"Generate a new code in the tax portal and retry this register — the other registers are unaffected and no certificate was issued for this one.",
	"error.attempt": "{attempt} of {max} · next retry manual",
	"error.timeout.summary": "The authority did not answer in time.",
	"error.timeout.remedy":
		"Nothing was lost — retry this register. If it times out again the authority is likely down, and the other registers are unaffected.",
	"error.compliance_failed.summary": "The authority refused the compliance certificate.",
	"error.compliance_failed.remedy":
		"The details below name what it objected to. Correct the register and retry it with a fresh one-time password.",
	"error.tests_failed.summary": "One of the mandatory test documents was rejected.",
	"error.tests_failed.remedy":
		"Each rejected document is listed below with the rule it broke. Fix the underlying setup and retry — this register keeps its compliance certificate, so no new code is needed.",
	"error.production_failed.summary": "The production certificate could not be issued.",
	"error.production_failed.remedy":
		"The test documents passed, so this is the last step only. Retry this register; it resumes from where it stopped.",
	"error.unknown.summary": "This register failed for a reason we could not classify.",
	"error.unknown.remedy":
		"The raw exchange is below. Retry the register, and quote the request id if you contact support.",
	"progress.retryOtp.label": "New one-time password",
	"progress.retryOtp.hint":
		"This register failed before its certificate was issued, so it needs a fresh code.",

	/* ── 12 Done ────────────────────────────────────────────────────────── */
	"done.title": "{company} is registered for e-invoicing",
	"done.body": { one: "{count} commercial register holds a live production certificate. Invoices you issue from now on are cryptographically stamped and cleared with the authority automatically.", other: "{count} commercial registers hold live production certificates. Invoices you issue from now on are cryptographically stamped and cleared with the authority automatically." },
	"done.outstanding": { one: "{count} register is still in draft and issues uncleared invoices until you finish it.", other: "{count} registers are still in draft and issue uncleared invoices until you finish them." },
	"done.reference": "setup reference {ref}",
	"done.completed": "completed {when}",
	"done.active": "What is active now",
	"done.active.p2a": "*Clearance for B2B invoices* — sent to the authority before delivery to the customer",
	"done.active.p2b": "*Reporting for B2C invoices* — submitted automatically within 24 hours",
	"done.active.p2c": "*QR code and cryptographic stamp* on every printed and PDF invoice",
	"done.active.p1a": "*QR code on every invoice* — compliant, with the hashed totals",
	"done.active.p1b": "*Tamper-evident archive* with invoice hash chaining",
	"done.active.p1c": "*Bilingual print format* in Arabic and English",
	"done.fact.certificates": "Certificates",
	"done.fact.fingerprint": "Fingerprint",
	"done.fact.renewal": "Renewal",
	"done.certValue": "{count} production · valid to {date}",
	"done.certCount": { one: "{count} production certificate", other: "{count} production certificates" },
	"done.renewalValue": "Reminder scheduled 60 days before expiry",
	"done.next": "Next steps",
	"done.invoice.title": "Issue your first cleared invoice",
	"done.invoice.body": "Create a sales invoice as usual — clearance happens on submit.",
	"done.invoice.cta": "New sales invoice",
	"done.finish.title": { one: "Finish the remaining register", other: "Finish the {count} remaining registers" },
	"done.finish.body":
		"Generate a fresh OTP and retry — the live registers are unaffected.",
	"done.finish.cta": "Open the run",
	"done.log.title": "View the e-invoicing log",
	"done.log.body": "Per-invoice clearance status, UUIDs and authority responses.",
	"done.log.cta": "Open log →",
	"done.another.title": "Another company",
	"done.another.body": { one: "{count} other company on this site is not registered yet.", other: "{count} other companies on this site are not registered yet." },
	"done.another.bodyAll": "Every company on this site is registered.",
	"done.another.cta": "Register another company",
	"done.support.title": "Something look wrong?",
	"done.support.body": "Quote reference {ref} and we can see the full trace.",
	"done.support.cta": "Message us on WhatsApp",

	"log.title": "E-invoicing log",
	"log.subtitle": "Every exchange with the authority, most recent first.",
	"log.register": "Register",
	"log.empty": "Nothing has been sent for this register yet.",
	"log.emptyRegisters": "No registers have been set up yet.",
	"log.col.at": "Time",
	"log.col.operation": "Operation",
	"log.col.outcome": "Outcome",
	"log.col.status": "HTTP",
	"log.col.duration": "Took",
	"log.outcome.ok": "Accepted",
	"log.outcome.rejected": "Rejected",
	"log.outcome.error": "Error",
	"log.outcome.timeout": "Timed out",
	"log.said": "The authority said",
	"log.ms": "{ms} ms",
	"log.seconds": "{s} s",
	"log.close": "Close",
	"log.openFor": "Log · {name}",
	"log.counts": { one: "{count} exchange", other: "{count} exchanges" },
	"log.refused": { one: "{count} refused", other: "{count} refused" },
	"log.backToSetup": "← Back to e-invoicing setup",

	"env.sandbox.name": "Sandbox",
	"env.simulation.name": "Simulation",
	"env.production.name": "Production",
	"env.sandbox.short": "Test only — these invoices do not count",
	"env.simulation.short": "Test only — these invoices do not count",
	"env.production.short": "Live — these invoices are legally filed",
	"env.sandbox.long":
		"This company is registered against the *sandbox* authority. Nothing here reaches the tax authority and *no invoice you issue counts as filed*. Certificates issued here are refused by the live service.",
	"env.simulation.long":
		"This company is registered against the *simulation* authority. It behaves like the live service but *no invoice you issue counts as filed*, and certificates issued here are refused by the live service.",
	"env.production.long":
		"This company is registered against the *live* authority. Every invoice you issue from now on is *filed with the tax authority for real*.",
	"env.unknown":
		"The server has not reported which authority this company is registered against, so we cannot tell you whether these invoices count. Treat them as test data until it does.",
	"env.label": "Authority",

	/* ── Guards and placeholders ────────────────────────────────────────── */
	"guard.failed.title": "We could not load your setup",
	"guard.failed.body":
		"{reason} Reload the page to try again — nothing has been submitted.",
	"guard.failed.reason": "The server did not answer.",
	"stub.back": "← Back to e-invoicing setup",
	"stub.log.title": "E-invoicing log",
	"stub.log.body":
		"Per-invoice clearance status, UUIDs and authority responses live here. It is outside this build — the onboarding flow is what has been implemented so far.",
	"stub.registers.title": "Registers",
	"stub.registers.body":
		"Managing certificates after go-live — renewals, retries and revocation — lives here. It is outside this build.",

	/* ── Validation ─────────────────────────────────────────────────────── */
	"validation.required": "Required.",
	"validation.digitsOnly": "Digits only.",
	"validation.company.required": "Choose the company to register.",
	"validation.tin.required": "Required. Find this on your VAT certificate.",
	"validation.tin.short": { one: "One digit short. A tax identification number is {length} digits and must begin and end with 3.", other: "{count} digits short. A tax identification number is {length} digits and must begin and end with 3." },
	"validation.tin.long": "Too long. A tax identification number is {length} digits.",
	"validation.tin.brackets": "A tax identification number must begin and end with 3.",
	"validation.crn.required": "Required. {count} digits, from the commercial register.",
	"validation.crn.length": "A commercial register number is {count} digits.",
	"validation.crn.duplicate": "This register is already in this setup.",
	"validation.legalName.required": "Required. Copy it from the taxpayer profile.",
	"validation.legalName.arabic": "This must be the Arabic legal name, in Arabic script.",
	"validation.registerName.required": "Required. This is shown on the invoice.",
	"validation.building.format": "The national address building number is 4 digits.",
	"validation.postal.format": "A postal code is 5 digits.",
	"validation.additional.format": "The additional number is 4 digits.",
	"validation.vatGroup.format": "A VAT group number is 15 digits.",
	"validation.otp.length": "An OTP is {count} digits.",

	/* ── Server responses ───────────────────────────────────────────────── */
	"api.fixHighlighted": "Fix the highlighted fields.",
	"api.otpAll": "Enter one complete code for every register.",
	"api.alreadyRunning": "Registration is already running; wait for it to finish.",
	"api.alreadyComplete": "This setup is complete and can no longer be edited.",
	"api.registerGone": "That register no longer exists.",
	"api.liveNoEdit": "A register holding a production certificate cannot be edited.",
	"api.liveNoRemove": "A register holding a production certificate cannot be removed.",
	"api.nothingToRetry": "Nothing to retry.",
	"api.stillRunning": "Registration is still running.",
	"api.noCompany": "No company is set up on this site yet.",
	"api.chooseCompany":
		"This site has several companies and no default. Set a default company, or open this page from the company you are registering.",
	"api.notSignedIn": "Your session has expired. Sign in again and reload this page.",
	"api.notPermitted": "You do not have permission to set up e-invoicing for this company.",
	"api.unreachable": "We could not reach the server. Check your connection and try again.",
	"mode.unavailable": "Not available",
	"mode.phase2.foot": "*Not included:* nothing — Phase 2 covers everything Phase 1 does.",
	"eligibility.blocker.noCountry": "{company} has no country set, so no tax authority can be identified.",
	"eligibility.blocker.countryUnsupported": "E-invoicing for {country} is not supported yet.",
	"eligibility.blocker.noTaxAccounts":
		"{company} has no VAT accounts configured. Set up tax accounts and an item tax template first.",
	"eligibility.note.waveIsAuthorityAssigned":
		"Confirm the authority has called you up for this obligation — it notifies taxpayers directly, and this cannot be checked from here.",
	"eligibility.because.registeredAndConfigured": "Your company is VAT registered and its tax accounts are configured.",
	"company.eyebrow": "Setup · which company",
	"company.title": "Which company are you registering?",
	"company.body":
		"A registration belongs to one company. Every answer that follows is stored against it, so this is settled first.",
	"company.unavailable": "Not available",
	"company.noneEligible":
		"No company on this site can be registered yet. Configure VAT accounts for at least one, then come back.",
	"company.status.draft": "In progress",
	"company.status.running": "Registering now",
	"company.status.partial": "Needs attention",
	"company.status.live": "Already registered",
	"entity.company.locked":
		"Chosen at the start of setup. Start again to register a different company.",
	"mode.noneAvailable":
		"This company cannot be registered yet. Clear the problems above, or choose another company.",
	"registers.doneAdding": "Done — review {count}",

	/* ── Step guides ────────────────────────────────────────────────────── */
	/*
	 * One panel per step, answering the question the screen itself does not:
	 * not "what do I type here" but "what is this for, and what happens if I get
	 * it wrong". Whoever does this setup is often not the person who understands
	 * the regulation, so each one states the consequence rather than the rule.
	 */
	"guide.show": "What is this step?",
	"guide.hide": "Hide",
	"guide.label": "Guidance for this step",

	"guide.company.title": "Choosing the company",
	"guide.company.b1":
		"Every answer after this is stored against this company, and certificates are issued per company. Pick the one whose invoices you are making compliant.",
	"guide.company.b2":
		"A company is registered once. Opening one that is already part-way through resumes it rather than starting again.",
	"guide.company.b3":
		"A company needs a country and VAT tax accounts before it can be registered. Anything missing is listed on its card.",

	"guide.mode.title": "Choosing your obligation",
	"guide.mode.b1":
		"Phase 1 puts a QR code on the printed invoice and transmits nothing. No certificate is issued, so no one-time password is needed.",
	"guide.mode.b2":
		"Phase 2 signs every invoice and clears or reports it to the authority. This is the one that needs certificates and codes.",
	"guide.mode.b3":
		"The authority decides which wave you are in and tells you directly. Nothing here can check that, so confirm it before choosing.",

	"guide.scope.title": "How many registers",
	"guide.scope.b1":
		"One certificate is issued per commercial register, not per company. A business trading under three CRNs needs three.",
	"guide.scope.b2":
		"The number you give only drives the progress counter. You can add or remove registers right up until you submit.",
	"guide.scope.b3":
		"If you are not sure how many you hold, check them on the Ministry of Commerce portal before continuing.",

	"guide.entity.title": "Your legal identity",
	"guide.entity.b1":
		"The Arabic legal name and the 15-digit tax number are embedded in every certificate and printed on every invoice.",
	"guide.entity.b2":
		"Both have to match the authority's records exactly. A mismatch is refused when the certificate is issued, not when you save.",
	"guide.entity.b3":
		"Check them on the authority's taxpayer lookup first. Correcting them afterwards means issuing new certificates.",

	"guide.registers.title": "Adding a register",
	"guide.registers.b1":
		"Each register needs its 10-digit CRN and the national address of the premises it trades from.",
	"guide.registers.b2":
		"The building number is four digits and the postal code five. The authority refuses anything else.",
	"guide.registers.b3":
		"This address is printed on the invoice and embedded in the certificate, so it has to be the registered address rather than a mailing one.",

	"guide.review.title": "Before you submit",
	"guide.review.b1":
		"This is the last point at which anything can be changed. After submission the register list is fixed for this run.",
	"guide.review.b2":
		"Check every number and address against your records. One wrong digit produces a valid certificate for the wrong premises.",
	"guide.review.b3":
		"Submitting queues one independent job per register, so a single failure does not stop the others.",

	"guide.otp.title": "One-time passwords",
	"guide.otp.b1":
		"Generate one code per register on the Fatoora portal. A code belongs to the register it was issued for and cannot be used for another.",
	"guide.otp.b2":
		"Each code lasts one hour and works once, so generate them now rather than ahead of time.",
	"guide.otp.b3":
		"The codes authorise certificate issuance and nothing else. They are not kept after the run and never appear on an invoice.",

	"guide.progress.title": "What is happening now",
	"guide.progress.b1":
		"Each register moves through five stages: a key pair, a certificate request, a compliance certificate, six test documents, then the production certificate.",
	"guide.progress.b2":
		"Registers run independently and at their own speed. One that fails can be retried on its own without disturbing the rest.",
	"guide.progress.b3":
		"You can close this page. The work continues on the server, and this board picks it up again when you come back.",

	"guide.done.title": "What happens next",
	"guide.done.b1":
		"Every live register now holds a production certificate. Invoices issued from them are cleared or reported for real.",
	"guide.done.b2":
		"The log records every exchange with the authority. It is where a rejected invoice is diagnosed.",
	"guide.done.b3":
		"Adding a commercial register later means registering that one too. The registers already live are unaffected.",
	"done.body.phase1": { one: "{count} commercial register is set up. Every invoice you issue carries a compliant QR code and is archived locally — nothing is transmitted to the authority.", other: "{count} commercial registers are set up. Every invoice you issue carries a compliant QR code and is archived locally — nothing is transmitted to the authority." },
	"done.certNone": "Not required for Phase 1",
	"done.renewalNone": "No certificate to renew",
	"done.invoice.title.phase1": "Issue your first compliant invoice",
	"done.invoice.body.phase1": "Create a sales invoice as usual — the QR code is added when you submit it.",
} as const satisfies Record<string, Message>;
