import { DataState } from "@/types";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

const initialState: DataState[] = [];

const dataSlice = createSlice({
  name: "data",
  initialState,
  reducers: {
    setData: (state, action: PayloadAction<DataState>) => {
      const newData = action.payload;
      const index = state.findIndex((item) => item.commercial_register_number === newData.commercial_register_number);
      if (index !== -1) {
        state[index] = newData;
      } else {
        state.push(newData);
      }
    },
    resetData: (state) => {
      state = [];
      return state
    },
    deleteData: (state, action: PayloadAction<DataState>) => {
      const itemIndex = state.findIndex(item => item.commercial_register_number === action.payload.commercial_register_number);
      if (itemIndex !== -1 ) state.splice(itemIndex, 1);
    }
  },
});

export const { setData, resetData, deleteData } = dataSlice.actions;
export default dataSlice.reducer;
