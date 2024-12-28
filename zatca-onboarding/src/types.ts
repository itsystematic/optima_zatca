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
  adding?: boolean;
  company: string | undefined;
  company_name_in_arabic: string;
  tax_id: string;
  commercial_register: CommercialData[];
  phase: string;
};

// export type MainData = {
//   otp?: string; more_info?: string & {
//     [k in
//       | "address_line1"
//       | "address_line2"
//       | "building_no"
//       | "city"
//       | "commercial_register_name"
//       | "commercial_register_number"
//       | "company"
//       | "company_name_in_arabic"
//       | "district"
//       | "tax_id"
//       | "pincode"
//       | "short_address"]: string;
//   };
// };

export type MainData = Omit<DataState, "commercial_register" | "adding"> & CommercialData;

export type Company = {
  [k in
    | "cost_center"
    | "country"
    | "default_bank_account"
    | "default_currency"
    | "doctype"
    | "name"]: string;
};
