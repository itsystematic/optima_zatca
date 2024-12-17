import commissionReducer from "@/data/commission";
import pageReducer from "@/data/currentPage";
import stepReducer from "@/data/currentStep";
import dataReducer from "@/data/dataSlice";
import editReducer from "@/data/editModal";
import { configureStore } from "@reduxjs/toolkit";
export const store = configureStore({
  reducer: {
    dataReducer,
    commissionReducer,
    pageReducer,
    stepReducer,
    editReducer
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
