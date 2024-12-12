import React from "react";

interface InputProps {
  input: {
    id: string;
    name: string;
    type: React.HTMLInputTypeAttribute;
  };
}

const FormInput: React.FC<InputProps> = ({ input }) => {
  return (
    <div className="relative z-0 w-full mb-5 group">
      <input
        type={input.type}
        name={input.name}
        id={input.id}
        className="block py-2.5 px-0 w-full text-sm text-gray-900 bg-transparent border-0 border-b-2 border-gray-300 appearance-none dark:text-white dark:border-gray-600 dark:focus:border-blue-500 focus:outline-none focus:ring-0 focus:border-[#483f61] peer"
        placeholder=" "
        required
      />
      <label
        htmlFor={input.id}
        className="peer-focus:font-medium absolute text-sm text-gray-500 dark:text-gray-400 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:start-0 rtl:peer-focus:translate-x-1/4 rtl:peer-focus:left-auto peer-focus:text-[#483f61] peer-focus:dark:text-[#483f61] peer-placeholder-shown:scale-100 peer-placeholder-shown:translate-y-0 peer-focus:scale-75 peer-focus:-translate-y-6"
      >
        {input.name}
      </label>
    </div>
  );
};

export default FormInput;
