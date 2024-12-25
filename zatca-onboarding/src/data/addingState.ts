import { createSlice, PayloadAction } from '@reduxjs/toolkit';



const initialState = {
    isAdding: false,
}



const addingState = createSlice({
    name: 'adding',
    initialState,
    reducers: {
        setIsAdding: (state, action: PayloadAction<boolean>) => {
            state.isAdding = action.payload
        }
    }
})

export const { setIsAdding } = addingState.actions
export default addingState.reducer