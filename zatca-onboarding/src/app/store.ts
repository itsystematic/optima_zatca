import commissionReducer from "@/data/commission";
import dataReducer from "@/data/dataSlice";
import stepsReducer from "@/data/stepSlice";
import { configureStore } from "@reduxjs/toolkit";
export const store = configureStore({
  reducer: {
    stepsReducer,
    dataReducer,
    commissionReducer
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
