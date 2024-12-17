import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setStep } from "@/data/currentStep";
import { Flex, Steps } from "antd";
import { AnimatePresence, motion } from "framer-motion";
import React, { ReactNode } from "react";
interface Props {
  steps: { id: number; title: string; component: ReactNode; }[];
  children: ReactNode;
}

const StepsContainer: React.FC<Props> = ({ steps, children }) => {
    const dispatch = useAppDispatch()
    const step = useAppSelector(state => state.stepReducer.currentStep);


  const onChange = (step: number) => {
    dispatch(setStep({currentStep: step}));
  };

  return (
    <Flex flex={1} align="center" justify="center" vertical>
      <Steps
        current={step}
        onChange={onChange}
        items={steps}
        className="w-1/2"
      />
      <AnimatePresence>
      <motion.div key={step} initial={{opacity: 0, scale: 0}} animate={{opacity: 1, scale: 1}}  className="flex w-full h-full">
      {children}
      </motion.div>
      </AnimatePresence>
    </Flex>
  );
};

export default StepsContainer;
