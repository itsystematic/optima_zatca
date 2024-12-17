import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { deactivateEdit } from "@/data/editModal";
import Step2 from "@/pages/Steps/Step2";
import { ConfigProvider, Modal } from "antd";



const EditingForm = () => {
  const dispatch = useAppDispatch();
  const editState = useAppSelector(state => state.editReducer);

  const onClose = () => {
    dispatch(deactivateEdit())
  }


  return (
    <ConfigProvider theme={{
      components: {
        Modal: {
          contentBg: '#ffffff99'
        }
      }
    }}>
    <Modal centered onCancel={onClose} open={editState.edit} footer className="w-[40%]">
      <Step2 edit={true} commercial={editState.commercial} />
    </Modal>
    </ConfigProvider>
  )
}

export default EditingForm