import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setStep } from "@/data/currentStep";
import { Flex, Steps } from "antd";
import { AnimatePresence, motion } from "framer-motion";
import React, { ReactNode } from "react";
interface Props {
  steps: { id: number; title: string; component: ReactNode }[];
  children: ReactNode;
}

const StepsContainer: React.FC<Props> = ({ steps, children }) => {
  const dispatch = useAppDispatch();
  const currentStep = useAppSelector((state) => state.stepReducer.currentStep);

  const validStep = (step: number) => {
    if (step > currentStep) return false;
    return true;
  }

  const onChange = (step: number) => {
    if (!validStep(step)) return;
    dispatch(setStep({ currentStep: step }));
  };

  return (
    <Flex flex={1} align="center" justify="center" vertical>
      <Steps
        current={currentStep}
        onChange={onChange}
        items={steps}
        className="w-1/2"
      />
      <AnimatePresence>
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex w-full h-full"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </Flex>
  );
};

export default StepsContainer;
