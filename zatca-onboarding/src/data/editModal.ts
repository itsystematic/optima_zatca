import { CommercialData } from "@/types";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface EditState {
  commercial: CommercialData;
  edit?: boolean;
}

const initialState: EditState = {
  commercial: {
    address_line1: "",
    address_line2: "",
    building_no: "",
    city: "",
    commercial_register_name: "",
    commercial_register_number: "",
    district: "",
    more_info: "",
    otp: "",
    pincode: "",
    short_address: "",
  },
  edit: false,
};

const editSlice = createSlice({
  name: "edit",
  initialState,
  reducers: {
    activateEdit: (state, action: PayloadAction<EditState>) => {
      state.edit = true;
      state.commercial = action.payload.commercial;
    },
    deactivateEdit: (state) => {
      state.edit = false;
      state.commercial = {...initialState.commercial}
    }
  },
});

export const { activateEdit, deactivateEdit } = editSlice.actions;
export default editSlice.reducer;
