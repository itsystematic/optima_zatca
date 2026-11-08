/** Values the backend stores in Zatca Main Settings.phase. */
export type Phase = "Phase One" | "Phase Two";
export type RegisterType = "main" | "multi";

/** One commercial register as register_company receives it. */
export interface CommercialRegister {
	commercial_register_name: string;
	commercial_register_number: string;
	short_address: string;
	building_no: string;
	address_line1: string;
	address_line2: string;
	city: string;
	district: string;
	pincode: string;
	otp: string;
	more_info: string;
}

export type RegisterField = Exclude<keyof CommercialRegister, "otp">;

export interface Company {
	name: string;
	company_name_in_arabic?: string | null;
	tax_id?: string | null;
}

/** A row of get_companies_registered. */
export interface RegisteredRow {
	company: string;
	company_name_in_arabic: string;
	tax_id: string;
	commercial_register_number: string;
	commercial_register_name: string;
	short_address: string;
	building_no: string;
	address_line1: string;
	address_line2: string;
	city: string;
	pincode: string;
	district: string;
	otp: string;
	phase: Phase;
}

export interface RegisterPayload {
	company: string;
	company_name_in_arabic: string;
	tax_id: string;
	phase: Phase;
	commercial_register: CommercialRegister[];
}

/** The "zatca" realtime event that zatca/setup.py and zatca/demo.py publish. */
export interface ZatcaEvent {
	message?: string;
	indicator?: string;
	percentage?: number;
	complete?: boolean;
	/** The Commercial Register's name, which is its CRN. */
	commercial_register_name?: string;
}
