export type CommercialData = {
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
  phase?: string; // Make only 'phase' optional
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

export type MainData = Omit<DataState, "commercial_register" | "adding"> &
  CommercialData;

export type Company = {
  [k in
    | "cost_center"
    | "country"
    | "default_bank_account"
    | "default_currency"
    | "doctype"
    | "name"]: string;
};
