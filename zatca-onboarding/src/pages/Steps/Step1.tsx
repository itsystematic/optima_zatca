import { useAppDispatch } from "@/app/hooks";
import { step1_schema } from "@/constants";
import { nextStep } from "@/data/stepSlice";
import { yupResolver } from "@hookform/resolvers/yup";
import { motion } from "motion/react";
import { useForm } from "react-hook-form";
const Step1 = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: yupResolver(step1_schema) });

  const dispatch = useAppDispatch();

  const onSubmit = (data: any) => {
    localStorage.setItem("data", JSON.stringify(data));
    // dispatch(setData(data));
    dispatch(nextStep());
  };
  return (
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
      <select className="select select-bordered " {...register("company")}>
        <option>Company 1</option>
        <option>Company 2</option>
        <option>Company 3</option>
        <option>Company 4</option>
      </select>
      {errors.company && <p>{errors.company.message}</p>}

      <input
        type="text"
        className="input   placeholder:font-extralight"
        placeholder="Company in Arabic"
        {...register("companyArabic")}
      />
      {errors.companyArabic && (
        <p className="font-medium text-red-500">
          {errors.companyArabic.message}
        </p>
      )}
      <input
        className="input w-full  placeholder:font-extralight"
        placeholder="TAX ID"
        {...register("tax_id")}
      />
      {errors.tax_id && (
        <p className="font-medium text-red-500">{errors.tax_id.message}</p>
      )}

      <input
        type="submit"
        className="btn bg-[#483f61] text-white"
        value="Next"
      />
    </motion.form>
  );
};

export default Step1;
