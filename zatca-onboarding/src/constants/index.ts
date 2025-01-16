import { CommercialData } from "@/types";
const __ = (s: string) => s;
const top_inputs = [
  {
    id: "commercial_register_name",
    name: "Commercial Register Name",
    rules: [
      { required: true, message: __("Commercial Register Name is required") },
    ],
  },
  {
    id: "commercial_register_number",
    name: "Commercial Register Number",
    rules: [
      {
        required: true,
        message: __("Commercial Register Number is required & Must be 10 digits"),
        pattern: /^\d{10}$/,
      },
    ],
    maxlength: 10,
    disabled: true,
  },
];

const LHSinputs = [
  {
    id: "short_address",
    name: "Short Address",
    rules: [{ required: true, message: __("Short Address is required") }],
    maxlength: 8,
  },
  {
    id: "building_no",
    name: "Building Number",
    rules: [
      {
        required: true,
        message: __("Building No. is required length of 4"),
        pattern: /^\d{4}$/,
      },
    ],
    maxlength: 4,
  },
  {
    id: "address_line1",
    name: "Street",
    rules: [{ required: true, message: __("Street is required") }],
  },
  {
    id: "address_line2",
    name: "Secondary No",
    rules: [{ required: true, message: __("Secondary No is required") }],
  },
];

const RHSinputs = [
  {
    id: "city",
    name: "City",
    rules: [{ required: true, message: __("City is required") }],
  },
  {
    id: "district",
    name: "District",
    rules: [{ required: true, message: __("District is required") }],
  },
  {
    id: "pincode",
    name: "Pincode",
    type: "number",
    maxlength: 5,
    rules: [
      {
        required: true,
        message: __("Pincode is required the length of 5"),
        pattern: /^\d{5}$/,
      },
    ],
  },
  {
    id: "more_info",
    name: "More Info",
  },
];

const step1Tour = [
  {
    title: __("Company Name"),
    description: __("Put your company name here"),
    // cover: (
    //   <img
    //     alt="tour.png"
    //     src="https://user-images.githubusercontent.com/5378891/197385811-55df8480-7ff4-44bd-9d43-a7dade598d70.png"
    //   />
    // ),
    target: __("firstInput"),
  },
  {
    title: __("Company Name in Arabic"),
    description: __("Put your company name in Arabic here"),
    target: "secondInput",
  },
  {
    title: __("TAX ID"),
    description: __("Please input ur tax id"),
    target: "thirdInput",
  },
];

const step3Tour = [
  {
    title: __("Branches Table"),
    description: __("Here u'll find all the branches u added including there data"),
    // cover: (
    //   <img
    //     alt="tour.png"
    //     src="https://user-images.githubusercontent.com/5378891/197385811-55df8480-7ff4-44bd-9d43-a7dade598d70.png"
    //   />
    // ),
    target: "branches_table",
  },
  {
    title: __("Actions!!"),
    description: __("In here you can edit delete ur branches"),
    target: "actions",
  },
  {
    title: __("All done!"),
    description: __("Check this box in order to go to the OTP page"),
    target: "otp_check",
  },
];

export const generateCommercials = () => {
  const array = Array.from<CommercialData>({ length: 20 }).map(
    (_, index) =>
      ({
        commercial_register_name: `Commercial Register Name ${index + 1}`,
        commercial_register_number: Math.floor(Math.random() * 10000000000).toString(),
        short_address: `Short Address ${index + 1}`,
        building_no: "1234",
        address_line1: `Street ${index + 1}`,
        address_line2: `Secondary No ${index + 1}`,
        city: `City ${index + 1}`,
        district: `District ${index + 1}`,
        pincode: "12345",
        more_info: `More Info ${index + 1}`,
      } as CommercialData)
  );
  return array;
};

export { LHSinputs, RHSinputs, step1Tour, step3Tour, top_inputs };
