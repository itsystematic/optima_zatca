import { createSlice } from "@reduxjs/toolkit";

interface PageState {
  currentPage: number;
}

const initialState: PageState = {
  currentPage: 0,
};

const PageSlice = createSlice({
  name: "page",
  initialState,
  reducers: {
    setCurrentPage: (state, action) => {
      state.currentPage = action.payload;
    },
  },
});

export const { setCurrentPage } = PageSlice.actions;
export default PageSlice.reducer;
