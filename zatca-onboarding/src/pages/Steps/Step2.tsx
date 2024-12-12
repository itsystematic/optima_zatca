import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { step2_schema } from "@/constants";
import { setData } from "@/data/dataSlice";
import { nextStep } from "@/data/stepSlice";
import { DataState } from "@/types";
import { yupResolver } from "@hookform/resolvers/yup";
import { motion } from "motion/react";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { FaCheckCircle } from "react-icons/fa";

interface Step2Props {
  item?: DataState;
  editingRef?: React.ForwardedRef<HTMLDialogElement>;
}

const Step2: React.FC<Step2Props> = (props) => {
  const {
    watch,
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm({ resolver: yupResolver(step2_schema) });
  const [openIndex, setOpenIndex] = useState(null);

  const toggleDetails = (index: any) => {
    setOpenIndex(openIndex === index ? null : index); // Toggle the state
  };

  const dispatch = useAppDispatch();
  const commission = useAppSelector(
    (state) => state.commissionReducer.commission
  );
  const data = useAppSelector((state) => state.dataReducer);

  const onSubmit = (data: any) => {
    const storedData = JSON.parse(localStorage.getItem("data") as string);
    const combinedData = { ...storedData, ...data } as DataState;
    if (!props.item) {
      dispatch(setData(combinedData));
      if (commission === "multi") {
        dispatch(setData(combinedData));
        resetFields();
      } else {
        dispatch(nextStep());
      }
    } else {
      dispatch(setData(combinedData));
      //@ts-ignore
      props.editingRef?.current?.close();
    }
  };

  const resetFields = () => {
    setValue("commercial_register_name", "");
    setValue("commercial_register_number", "");
    setValue("short_address", "");
    setValue("building_no", "");
    setValue("city", "");
    setValue("address_line1", "");
    setValue("address_line2", "");
    setValue("district", "");
    setValue("pincode", "");
  };

  const isCommission = () => {
    if (commission === "multi" && !props.editingRef) {
      return true
    }
    return false
  }

  const isValid = () => {
    if (watch("commercial_register_number")?.length === 10 && watch('commercial_register_name').length) {
      return true
    }
    return false
  }

  useEffect(() => {
    if (!props.item) return;
    setValue("commercial_register_name", props.item.commercial_register_name);
    setValue("commercial_register_number", props.item.commercial_register_number);
    setValue("short_address", props.item.short_address);
    setValue("building_no", props.item.building_no);
    setValue("city", props.item.city);
    setValue("address_line1", props.item.address_line1);
    setValue("address_line2", props.item.address_line2);
    setValue("district", props.item.district);
    setValue("pincode", props.item.pincode);
  }, [props.item]);

  return (
    <>
    <div className={`flex h-full w-full gap-24 p-5 ${!isCommission() && 'justify-center gap-5'}`}>
      {isCommission() ? (
        <div className="h-full w-1/3 bg-[#959ca790] rounded-md flex flex-col gap-5">
     {data.map((item, index) => (
        <div key={index} className="group relative">
          <div
            className="bg-[#483f61] text-white p-4 rounded-md cursor-pointer transition-all duration-300 ease-in-out"
            onClick={() => toggleDetails(index)}
          >
            <summary className="text-xl font-semibold">
              {item.commercial_register_name}
            </summary>
          </div>

          <div
            className={`mt-4 bg-[#595c7a] text-white p-2 rounded-md transition-all duration-500 ease-in-out transform ${
              openIndex === index ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
            } overflow-hidden`}
          >
            <p><strong>Short Address:</strong> {item.short_address}</p>
            <p><strong>City:</strong> {item.city}</p>
            <p><strong>Building No:</strong> {item.building_no}</p>
            <p><strong>Address Line 1:</strong> {item.address_line1}</p>
            <p><strong>Address Line 2:</strong> {item.address_line2}</p>
            <p><strong>District:</strong> {item.district}</p>
            <p><strong>Postal Code:</strong> {item.pincode}</p>
            <p><strong>Commercial Register Number:</strong> {item.commercial_register_number}</p>
          </div>
        </div>
      ))}
        
      </div>
      ): null}
      <motion.form
        initial={{ x: "100%" }}
        animate={{ x: "0%" }}
        exit={{ x: "-100%" }}
        transition={{
          type: "spring",
          stiffness: 100,
          damping: 20,
        }}
        className="form-control justify-center gap-3 h-full w-[40%] bg-transparent"
        onSubmit={handleSubmit(onSubmit)}
      >
        {isValid() ? (
          <h1 className="flex gap-2 items-center">
            Commercial Information <FaCheckCircle className="text-green-700" />
          </h1>
        ) : null}
                <input
          type="text"
          className="input   placeholder:font-extralight"
          placeholder="Commercial Register Name"
          {...register("commercial_register_name")}
        />
        <input
          type="text"
          className="input   placeholder:font-extralight"
          placeholder="Commercial Register Number"
          {...register("commercial_register_number")}
          disabled={props.editingRef ? true : false}
        />
        {errors.commercial_register_number && (
          <p className="font-medium text-red-500">
            {errors.commercial_register_number.message}
          </p>
        )}
        {isValid() ? (
          <>
            <h1>Saudi National Address Components</h1>
            <div className="flex gap-3">
              <div className="flex flex-col gap-2 flex-grow">
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="Short Address"
                  {...register("short_address")}
                />
                {errors.short_address && (
                  <p className="font-medium text-red-500">
                    {errors.short_address.message}
                  </p>
                )}
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="Building No"
                  {...register("building_no")}
                />
                {errors.building_no && (
                  <p className="font-medium text-red-500">
                    {errors.building_no.message}
                  </p>
                )}
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="Street"
                  {...register("address_line1")}
                />
                {errors.address_line1 && (
                  <p className="font-medium text-red-500">
                    {errors.address_line1.message}
                  </p>
                )}
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="Secondary No"
                  {...register("address_line2")}
                />
                {errors.address_line2 && (
                  <p className="font-medium text-red-500">
                    {errors.address_line2.message}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-2 flex-grow">
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="City/Town"
                  {...register("city")}
                />
                {errors.city && (
                  <p className="font-medium text-red-500">
                    {errors.city.message}
                  </p>
                )}
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="District"
                  {...register("district")}
                />
                {errors.district && (
                  <p className="font-medium text-red-500">
                    {errors.district.message}
                  </p>
                )}
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="Postal Code"
                  {...register("pincode")}
                />
                {errors.pincode && (
                  <p className="font-medium text-red-500">
                    {errors.pincode.message}
                  </p>
                )}
                <input
                  type="text"
                  className="input input-md placeholder:font-extralight"
                  placeholder="More Info (Optional)"
                  {...register("more_info")}
                />
              </div>
            </div>
          </>
        ) : null}
        <input
          type="submit"
          className="btn bg-[#483f61] text-white border-0"
          value={props.item || commission === "multi" ? "Save" : "Next"}
        />
      </motion.form>
    </div>
    <div className={`justify-end h-full flex items-end p-5 w-[15%] ${!isCommission() ? 'hidden' : ''}`}>
      <button onClick={() => dispatch(nextStep())} className="btn bg-[#483f61] text-white w-full border-0 disabled:cursor-not-allowed disabled:opacity-50" disabled={!data.length}>Next</button>
    </div>
      </>
  );
};

export default Step2;
