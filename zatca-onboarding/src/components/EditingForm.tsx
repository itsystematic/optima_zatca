import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { deactivateEdit } from "@/data/editModal";
import Step2 from "@/pages/Steps/Step2";
import { Modal } from "antd";

const EditingForm = () => {
  const dispatch = useAppDispatch();
  const editState = useAppSelector((state) => state.editReducer);

  const onClose = () => {
    dispatch(deactivateEdit());
  };

  return (
    <Modal
      centered
      onCancel={onClose}
      open={editState.edit}
      footer
      className="w-[25%] "
    >
      <Step2 edit={true} commercial={editState.commercial} />
    </Modal>
  );
};

export default EditingForm;
