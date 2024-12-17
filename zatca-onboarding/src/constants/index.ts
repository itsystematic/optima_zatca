const top_inputs = [
  {
    id: "commercial_register_name",
    name: "Commercial Register Name",
    rules: [
      { required: true, message: "Commercial Register Name is required" },
    ],
  },
  {
    id: "commercial_register_number",
    name: "Commercial Register Number",
    rules: [
      { required: true, message: "Commercial Register Number is required & Must be 10 digits", pattern: /^\d{10}$/ },
    ],
    maxlength: 10,
    disabled: true,
  },
];

const LHSinputs = [
  {
    id: "short_address",
    name: "Short Address",
    rules: [{ required: true, message: "Short Address is required" }],
    maxlength: 8
  },
  {
    id: "building_no",
    name: "Building Number",
    rules: [{ required: true, message: "Building No. is required length of 4", pattern: /^\d{4}$/ }],
    maxlength: 4
  },
  {
    id: "address_line1",
    name: "Street",
    rules: [{ required: true, message: "Street is required" }],
  },
  {
    id: "address_line2",
    name: "Secondary No",
    rules: [{ required: true, message: "Secondary No is required" }],
  },
];

const RHSinputs = [
  {
    id: "city",
    name: "City",
    rules: [{ required: true, message: "City is required" }],
  },
  {
    id: "district",
    name: "District",
    rules: [{ required: true, message: "District is required" }],
  },
  {
    id: "pincode",
    name: "Pincode",
    type: "number",
    maxlength: 5,
    rules: [{ required: true, message: "Pincode is required the length of 5", pattern: /^\d{5}$/ }],
  },
  {
    id: "more_info",
    name: "More Info",
  },
];

export { LHSinputs, RHSinputs, top_inputs };
