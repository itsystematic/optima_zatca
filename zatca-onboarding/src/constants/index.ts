import * as Yup from 'yup';

export const step1_schema = Yup.object().shape({
    company: Yup.string().required("Company is required"),
    tax_id: Yup.string()
      .matches(/^\d{15}$/, "TAX ID must be 15 digits")
      .required("TAX ID is required"),
    companyArabic: Yup.string().required("Company in Arabic is required"),
  });

export const step2_schema = Yup.object().shape({
    commercial_register_name: Yup.string().required("Commercial Register Name is required"),
    commercial_register_number: Yup.string().matches(/^\d{10}$/, "Commercial Register must be 10 digits").required("Commercial Register is required"),
    short_address: Yup.string().required("Short Address is required"),
    building_no: Yup.string().required("Building Number is required"),
    address_line1: Yup.string().required("Street is required"),
    address_line2: Yup.string().required("Secondary No is required"),
    city: Yup.string().required("City is required"),
    district: Yup.string().required("District is required"),
    pincode: Yup.string().matches(/^\d{5}$/, "Pincode must be 5 digits").required("Pincode is required"),
    more_info: Yup.string().optional(),
  });