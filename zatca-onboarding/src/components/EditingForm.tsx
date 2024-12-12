import Step2 from "@/pages/Steps/Step2";
import { DataState } from "@/types";
import React, { forwardRef } from "react";
import { IoMdClose } from "react-icons/io";

interface EditingProps {
  item: DataState;
  setEditingItem: React.Dispatch<React.SetStateAction<DataState | null>>;
}

const EditingForm = forwardRef<HTMLDialogElement, EditingProps>(
  (props, ref) => {
    const handleClose = () => {
      if (ref && typeof ref !== "function" && ref.current) {
        ref.current.close(); // Close the dialog
        props.setEditingItem(null);
      }
    };
    console.log(props.item);
    return (
      <dialog ref={ref} id="my_modal_2" className="modal">
        <div className="modal-box max-h-[80vh] pb-0 max-w-[65vw] px-0 bg-[#cccfd490] flex flex-col h-screen rounded-sm">
          <button
            onClick={handleClose}
            className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2 text-lg"
          >
            <IoMdClose />
          </button>
          <div className="flex justify-center items-center h-full">
          <Step2 item={props.item} editingRef={ref} />
          </div>
        </div>
      </dialog>
    );
  }
);

export default EditingForm;
