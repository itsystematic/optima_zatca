import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { addOTP } from "@/data/dataSlice";
import { forwardRef, useState } from "react";
import OTPInput from "react-otp-input";

const OTP = forwardRef<HTMLDialogElement>((_, ref) => {
  const state = useAppSelector((state) => state.dataReducer);
const dispatch = useAppDispatch();
  // Maintain OTP state as an object where keys are `commercial_register_name`
  const [otpValues, setOtpValues] = useState<{ [name: string]: string }>({});
    const [loading, setisLoading] = useState<boolean>(false);
  // Update the OTP value for a specific commercial entry
  const handleOtpChange = (name: string, value: string) => {
    setOtpValues((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async () => {
      setisLoading(true);
      try {
          dispatch(addOTP(otpValues))
          console.log(state);
          const data = await frappe.call({
              method: 'optima_zatca.zatca.api.register_company_phase_two',
              args: state
          })

          console.log(data.message);
      }catch (err) {
        console.log(err);
      }

    // (ref as React.RefObject<HTMLDialogElement>).current?.close();
  };

  return (
    <dialog ref={ref} className="modal">
      <div className="modal-box h-[50rem] overflow-auto">
        <h3 className="font-bold text-lg">Please Enter The OTP!</h3>
        <div className="pb-14">
          {state.commercial_register.map((commercial, index) => (
            <div key={index} className="flex flex-col gap-5 items-center justify-between py-6">
              <div className="font-bold text-lg">{commercial.commercial_register_name}</div>
              <OTPInput
                value={otpValues[commercial.commercial_register_name] || ""} // Bind specific OTP
                onChange={(value) => handleOtpChange(commercial.commercial_register_name, value)} // Update specific OTP
                numInputs={5}
                renderSeparator={<span className="px-2">-</span>}
                renderInput={(props) => (
                  <input
                    {...props}
                    className="w-12 h-12 text-center border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg"
                  />
                )}
              />
            </div>
          ))}
        </div>
        <div className="modal-action">
          <button
            onClick={handleSubmit}
            className="btn bg-[#483f61] text-white disabled:opacity-50"
            disabled={
              Object.keys(otpValues).length < state.commercial_register.length || 
              Object.values(otpValues).some((otp) => otp.length !== 5) // Ensure all OTPs are entered
            }
          >
            {loading ? <span className="loading loading-ring text-white loading-lg"></span> : 'Submit'} 
          </button>
        </div>
      </div>
      <form method="dialog" className="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  );
});

export default OTP;
