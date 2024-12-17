import { createSlice, PayloadAction } from "@reduxjs/toolkit";


interface Step {
    currentStep: number;
}

const initialState: Step = {
    currentStep: 0
}


const StepSlice = createSlice({
    name: 'step',
    initialState,
    reducers: {
        setStep: (state, action: PayloadAction<Step>) => {
          state.currentStep = action.payload.currentStep;  
        }
    }
})


export const { setStep } = StepSlice.actions;
export default StepSlice.reducer;