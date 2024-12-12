import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type Commission = {
  commission: string;
};

const initialState: Commission = {
  commission: "",
};

const commissionSlice = createSlice({
  name: "commission",
  initialState,
  reducers: {
    setCommission: (state, action: PayloadAction<Commission>) => {
      state.commission = action.payload.commission;
    },
  },
});


export const { setCommission } = commissionSlice.actions;
export default commissionSlice.reducer;