import { createSlice } from "@reduxjs/toolkit";

interface StepState {
  completed: boolean;
  id: number;
  label: string;
  active: boolean;
}

const initialState: StepState[] = [
  {
    id: 1,
    label: "Company Details",
    completed: false,
    active: true,
  },
  {
    id: 2,
    label: "Company Address",
    completed: false,
    active: false,
  },
  {
    id: 3,
    label: "Company Units",
    completed: false,
    active: false,
  },
];

const stepSlice = createSlice({
  name: "step",
  initialState,
  reducers: {
    nextStep: (state: StepState[]) => {
      const activeStep = state.findIndex((step) => step.active);
      state[activeStep].active = false;
      state[activeStep + 1].active = true;
    },
    prevStep: (state: StepState[]) => {
      const activeStep = state.findIndex((step) => step.active);
      state[activeStep].active = false;
      state[activeStep - 1].active = true;
    },
  },
});

export const { nextStep, prevStep } = stepSlice.actions;
export default stepSlice.reducer;
