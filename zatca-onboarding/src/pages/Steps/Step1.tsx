import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { step1_schema } from "@/constants";
import { setData } from "@/data/dataSlice";
import { nextStep } from "@/data/stepSlice";
import { Company, DataState } from "@/types";
import { yupResolver } from "@hookform/resolvers/yup";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";



const Step1 = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: yupResolver(step1_schema) });
  
  const [companies, setCompanies] = useState<Company[]>([]);

  const dataState = useAppSelector(state => state.dataReducer);
  const dispatch = useAppDispatch();

  const onSubmit = (data: DataState | any) => {
    dispatch(setData({...dataState, ...data}));
    dispatch(nextStep());
  };

  useEffect(() => {
    if (isDev) {
      setCompanies([{name: 'anacompnay', cost_center: '123123', country: 'eg', default_bank_account: '123123', default_currency: 'EGP', doctype:'Company'}])
      return;
    }
    const companies = frappe.get_list('Company');
    setCompanies(companies);
  }, [])



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
      {companies.map((company: Company, index) => (
        <option key={index}>{company.name}</option>
      ))}
        {/* <option>Company 1</option>
        <option>Company 2</option>
        <option>Company 3</option>
        <option>Company 4</option> */}
      </select>
      {errors.company && <p>{errors.company.message}</p>}

      <input
        type="text"
        className="input   placeholder:font-extralight"
        placeholder="Company in Arabic"
        {...register("company_name_in_arabic")}
      />
      {errors.company_name_in_arabic && (
        <p className="font-medium text-red-500">
          {errors.company_name_in_arabic.message}
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
