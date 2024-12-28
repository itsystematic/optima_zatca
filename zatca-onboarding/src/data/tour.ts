import { createSlice } from "@reduxjs/toolkit";

type TourState = {
    open: boolean;
    steps: [];
}


const initialState: TourState = {
    open: false,
    steps: []
}


const tourSlice = createSlice({
    name: 'tour',
    initialState,
    reducers: {
        openTour: (state) => {
            state.open = true;
        },
        closeTour: (state) => {
            state.open = false;
        },
        setTourSteps: (state, action) => {
            state.steps = action.payload;
        }
    }
})


export const { closeTour, openTour, setTourSteps } = tourSlice.actions;
export default tourSlice.reducer;