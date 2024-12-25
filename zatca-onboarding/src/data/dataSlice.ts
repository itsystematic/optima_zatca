import { CommercialData, DataState } from "@/types";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

const initialState: DataState = {
  phase: "",
  tax_id: "",
  company: undefined,
  commercial_register: [],
  company_name_in_arabic: "",
  adding: false,
};

const dataSlice = createSlice({
  name: "data",
  initialState,
  reducers: {
    setData: (state, action: PayloadAction<DataState>) => {
      state = action.payload;
      return state;
    },
    addCommercial: (state, action: PayloadAction<CommercialData>) => {
      const commercialIndex = state.commercial_register.findIndex(
        (commercial) =>
          commercial.commercial_register_number ===
          action.payload.commercial_register_number
      );

      if (commercialIndex === -1) {
        state.commercial_register.push(action.payload);
      } else {
        state.commercial_register[commercialIndex] = action.payload;
      }
    },
    deleteCommercial: (state, action: PayloadAction<CommercialData>) => {
      // Finding commercial index in the state

      const commercialIndex = state.commercial_register.findIndex(
        (commercial) =>
          commercial.commercial_register_number ===
          action.payload.commercial_register_number
      );

      // If it doesn't exist pass

      if (commercialIndex === -1) return;

      // Remove the commercial from the state

      state.commercial_register.splice(commercialIndex, 1);

      return state;
    },
    addOTP: (state, action: PayloadAction<{ [name: string]: string }>) => {
      const otpValues = action.payload;

      // Update each commercial entry's OTP based on the names provided in `otpValues`
      state.commercial_register.forEach((commercial) => {
        if (otpValues[commercial.commercial_register_number]) {
          commercial.otp = otpValues[commercial.commercial_register_number];
        }
      });
    },
    resetData: () => initialState,
  },
});

export const { deleteCommercial, addCommercial, setData, addOTP, resetData } =
  dataSlice.actions;
export default dataSlice.reducer;
