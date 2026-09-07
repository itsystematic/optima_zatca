import type { Address, ChecklistItem, City, Company, Guidance, LifecycleStep, Setup } from "../types";

/**
 * Reference data the mock backend serves. When this is replaced by Frappe, the
 * companies come from the Company doctype, the cities from a link field, and the
 * guidance from the country profile registered in `optima_zatca.zatca.profile`.
 */

export const COMPANIES: Company[] = [
	{
		name: "Kandil Glass Industries",
		linked: true,
		defaultTin: "3001234567890",
		defaultLegalNameAr: "مصنع قنديل للزجاج المحدودة",
		eligible: true,
		blockers: [],
		status: "not_started",
	},
	{
		name: "Kandil Trading Co.",
		linked: true,
		defaultTin: "",
		defaultLegalNameAr: "",
		eligible: true,
		blockers: [],
		status: "not_started",
	},
	{
		// no tax accounts, so it cannot be registered — the picker has to be able
		// to show a company it must refuse, or that path is never exercised
		name: "Gulf Float Holdings",
		linked: false,
		defaultTin: "",
		defaultLegalNameAr: "",
		eligible: false,
		blockers: [{ key: "eligibility.blocker.noTaxAccounts", params: { company: "Gulf Float Holdings" } }],
		status: "not_started",
	},
];

export const CITIES: City[] = [
	"Riyadh",
	"Jeddah",
	"Dammam",
	"Al Khobar",
	"Madinah",
	"Makkah",
	"Abha",
	"Tabuk",
	"Buraydah",
	"Hail",
].map((name) => ({ name }));

const LIFECYCLE: LifecycleStep[] = [
	{
		key: "keys",
		title: "A key pair is generated",
		body: "A private key is created and never leaves this server. Every invoice you issue will be signed with it.",
		actor: "this system",
	},
	{
		key: "csr",
		title: "A certificate is requested",
		body: "The request carries your commercial register, tax number and address, and is submitted with the one-time password from the portal.",
		actor: "this system",
	},
	{
		key: "compliance",
		title: "A compliance certificate is issued",
		body: "This certificate proves the system works. It cannot yet be used for real invoices.",
		actor: "the authority",
	},
	{
		key: "tests",
		title: "Six documents are checked",
		body: "One of every document type you can issue is signed and submitted, so the authority can confirm they are valid before trusting real ones.",
		actor: "the authority",
	},
	{
		key: "production",
		title: "The production certificate arrives",
		body: "From this point your invoices are cleared or reported for real, and each one carries a QR code a buyer can verify.",
		actor: "the authority",
	},
];

const CHECKLIST: ChecklistItem[] = [
	{
		key: "tin",
		title: "Your 15-digit tax number",
		body: "It begins and ends with 3. Check it on the authority's taxpayer lookup before you start.",
	},
	{
		key: "registers",
		title: "Every commercial register number",
		body: "Ten digits each. One certificate is issued per register, so have them all to hand.",
	},
	{
		key: "address",
		title: "The national address of each register",
		body: "Building number, street, district, city and postal code. The building number is four digits and the postal code five.",
	},
	{
		key: "arabic",
		title: "Your legal name in Arabic",
		body: "Exactly as registered. It is printed on every invoice and embedded in the certificate.",
	},
	{
		key: "otp",
		title: "A one-time password per register",
		body: "Generated on the portal. Each is valid for one hour and can be used once, so generate them when you reach the last step.",
	},
];

export const GUIDANCE: Guidance = {
	lifecycle: LIFECYCLE,
	checklist: CHECKLIST,
	portalUrl: "https://fatoora.zatca.gov.sa",
	otpTtlMinutes: 60,
};

export const EMPTY_ADDRESS: Address = {
	buildingNumber: "",
	street: "",
	district: "",
	city: "",
	postalCode: "",
	country: "Saudi Arabia",
	additionalNumber: "",
	vatGroupNumber: "",
};

export function emptySetup(company = COMPANIES[0].name): Setup {
	return {
		id: "SETUP-0001",
		company,
		// the stand-in never talks to a real authority, and says so
		environment: "sandbox",
		status: "not_started",
		step: "mode",
		phase: null,
		scope: null,
		entity: null,
		entityVerifiedOn: null,
		expectedRegisters: null,
		registers: [],
		acknowledged: false,
		reference: null,
		startedAt: null,
		completedAt: null,
		modified: new Date().toISOString(),
	};
}

/** The five branches the artboards were drawn with, for the demo scenarios. */
export const DEMO_REGISTERS: { registerName: string; crn: string; address: Address }[] = [
	{
		registerName: "Riyadh — Head office",
		crn: "1010512345",
		address: {
			...EMPTY_ADDRESS,
			buildingNumber: "8734",
			street: "King Fahd Road",
			district: "Al Olaya",
			city: "Riyadh",
			postalCode: "12211",
		},
	},
	{
		registerName: "Jeddah — Coastal plant",
		crn: "4030298877",
		address: {
			...EMPTY_ADDRESS,
			buildingNumber: "2219",
			street: "Al Andalus Street",
			district: "Al Rawdah",
			city: "Jeddah",
			postalCode: "23434",
		},
	},
	{
		registerName: "Dammam — East depot",
		crn: "2050071234",
		address: {
			...EMPTY_ADDRESS,
			buildingNumber: "4410",
			street: "Prince Mohammed Street",
			district: "Al Adamah",
			city: "Dammam",
			postalCode: "32241",
		},
	},
	{
		registerName: "Khobar — Showroom",
		crn: "2051664401",
		address: {
			...EMPTY_ADDRESS,
			buildingNumber: "7712",
			street: "Prince Turkey Street",
			district: "Al Aqrabiyah",
			city: "Al Khobar",
			postalCode: "34423",
		},
	},
	{
		registerName: "Madinah — Warehouse",
		crn: "4650033120",
		address: {
			...EMPTY_ADDRESS,
			buildingNumber: "1902",
			street: "Sultanah Road",
			district: "Al Rayyan",
			city: "Madinah",
			postalCode: "42311",
		},
	},
];
