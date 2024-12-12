export type DataState = {
  [k in
    | "commercial_register_name"
    | "company"
    | "tax_id"
    | "companyArabic"
    | "commercial_register_number"
    | "short_address"
    | "building_no"
    | "address_line1"
    | "address_line2"
    | "city"
    | "district"
    | "pincode"
    | "more_info"]: string;
};
