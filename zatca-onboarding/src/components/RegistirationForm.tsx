import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { prevStep } from "@/data/stepSlice";
import React, { forwardRef, Fragment, useEffect, useState } from "react";
import { IoIosArrowBack } from "react-icons/io";
import Form from "./Form";

interface RegistirationFormProps {
  img: string;
  children?: React.ReactNode[];
  handleRegistirationBack?: () => void;
}

const RegistirationForm = forwardRef<HTMLDialogElement, RegistirationFormProps>(
  (props, ref) => {
    return (
      <Form ref={ref}>
        <RegistirationFormChildren img={props.img} handleRegistirationBack={props.handleRegistirationBack}>
          {props.children}
        </RegistirationFormChildren>
      </Form>
    );
  }
);

const RegistirationFormChildren: React.FC<
  RegistirationFormProps & { children?: React.ReactNode }
> = ({ img, children , handleRegistirationBack}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const stepState = useAppSelector((state) => state.stepsReducer);
  const dispatch = useAppDispatch();
  useEffect(() => {
    setCurrentStep(stepState.findIndex((step) => step.active) + 1);
  }, [stepState]);

  const handleBack = () => {
    if (currentStep > 1) {
      dispatch(prevStep())
    }
    else {
      handleRegistirationBack?.()
    }
  }

  return (
    <Fragment>
      {currentStep !== 3 ?  (

        <button
        onClick={handleBack}
        className="btn btn-sm btn-circle btn-ghost absolute left-2 top-2 text-lg"
        >
        <IoIosArrowBack />
      </button>
      ) : null}

      <div className="flex justify-center items-center">
        <ul className="steps steps-horizontal w-1/2">
          {stepState.map((step, index) => (
            <li
              data-content={currentStep > step.id ? `✓` : index + 1}
              key={index}
              className={`step ${
                step.id === currentStep
                  ? "step-neutral"
                  : currentStep > step.id
                  ? "step-accent"
                  : ""
              }`}
            >
              {step.label}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex justify-center items-center h-full gap-30 overflow-hidden">
        {/* {currentStep !== 3 ? null : (
          <div className="flex gap-5 justify-center items-center h-[80%] w-1/2">
        
          <img src={img} alt="" />
        </div>
        )} */}
        {children &&
          children.map((child, index) =>
            stepState[index]?.active ? <Fragment key={index}>{ child }</Fragment> : null
          )}
      </div>
    </Fragment>
  );
};

export default RegistirationForm;
