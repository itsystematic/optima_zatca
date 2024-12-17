export type CommercialData = {
  [k in
    | "commercial_register_name"
    | "commercial_register_number"
    | "short_address"
    | "building_no"
    | "address_line1"
    | "address_line2"
    | "city"
    | "district"
    | "pincode"
    | "otp"
    | "more_info"]: string;
};

export type DataState = {
  company: string;
  company_name_in_arabic: string;
  tax_id: string;
  commercial_register: CommercialData[];
};

export type Company = {
  [k in
    | "cost_center"
    | "country"
    | "default_bank_account"
    | "default_currency"
    | "doctype"
    | "name"]: string;
};